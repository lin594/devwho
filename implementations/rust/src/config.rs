use std::{
    collections::{BTreeMap, HashMap, HashSet},
    env, fs,
    path::{Path, PathBuf},
};
use toml::Value;

pub type Env = BTreeMap<String, String>;
pub type Result<T> = std::result::Result<T, String>;
#[derive(Clone, Debug)]
pub struct Profile {
    pub name: String,
    pub git: Value,
    pub ssh: Value,
    pub github: Value,
    pub env: Env,
    pub unset: Vec<String>,
}
#[derive(Clone, Debug)]
pub struct Config {
    pub path: PathBuf,
    pub profiles: HashMap<String, Profile>,
    pub default: Option<String>,
    pub shortcut: Option<String>,
    pub handoff: bool,
}
fn table<'a>(
    v: &'a Value,
    field: &str,
    allowed: Option<&[&str]>,
) -> Result<&'a toml::map::Map<String, Value>> {
    let t = v.as_table().ok_or(format!("{field} must be a table"))?;
    if let Some(a) = allowed {
        for k in t.keys() {
            if !a.contains(&k.as_str()) {
                return Err(format!("Unknown field in {field}: {k}"));
            }
        }
    }
    Ok(t)
}
fn string<'a>(v: Option<&'a Value>, field: &str, nonempty: bool) -> Result<&'a str> {
    let s = v
        .and_then(Value::as_str)
        .ok_or(format!("{field} must be a string without NUL"))?;
    if s.contains('\0') || nonempty && s.trim().is_empty() {
        return Err(format!("{field} must be a nonempty string without NUL"));
    }
    Ok(s)
}
fn valid_profile(s: &str) -> bool {
    let mut c = s.chars();
    matches!(c.next(),Some(x) if x.is_ascii_alphanumeric())
        && c.all(|x| x.is_ascii_alphanumeric() || "_.-".contains(x))
}
pub fn valid_env(s: &str, internal: bool) -> Result<()> {
    let mut c = s.chars();
    if !matches!(c.next(),Some(x) if x.is_ascii_alphabetic()||x=='_')
        || !c.all(|x| x.is_ascii_alphanumeric() || x == '_')
    {
        return Err("Invalid environment variable name".into());
    }
    let unsafe_names = [
        "BASH_ENV",
        "ENV",
        "BASHOPTS",
        "SHELLOPTS",
        "IFS",
        "CDPATH",
        "ZDOTDIR",
        "PS4",
        "PROMPT_COMMAND",
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    ];
    if unsafe_names.contains(&s)
        || s.starts_with("__DEVWHO")
        || s.starts_with("__devwho")
        || s.starts_with("DEVWHO_") && !(internal && s == "DEVWHO_PROFILE")
        || ((s == "GIT_CONFIG_COUNT"
            || s.starts_with("GIT_CONFIG_KEY_")
            || s.starts_with("GIT_CONFIG_VALUE_"))
            && !(internal && is_runtime(s)))
    {
        return Err(format!("Reserved environment variable: {s}"));
    }
    Ok(())
}
pub fn is_runtime(s: &str) -> bool {
    if s == "GIT_CONFIG_COUNT" {
        return true;
    }
    for pre in ["GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"] {
        if let Some(n) = s.strip_prefix(pre) {
            return !n.is_empty() && n.bytes().all(|b| b.is_ascii_digit());
        }
    }
    false
}
fn git_key(s: &str) -> bool {
    if s.chars().any(|c| matches!(c, '\n' | '\r' | '\0')) {
        return false;
    }
    let parts: Vec<_> = s.split('.').collect();
    if parts.len() < 2 {
        return false;
    }
    for p in [parts[0], parts[parts.len() - 1]] {
        let mut c = p.chars();
        if !matches!(c.next(),Some(x) if x.is_ascii_alphabetic())
            || !c.all(|x| x.is_ascii_alphanumeric() || x == '-')
        {
            return false;
        }
    }
    if parts.len() == 3 && parts[1].is_empty() {
        return false;
    }
    true
}
fn empty_table() -> Value {
    Value::Table(Default::default())
}
fn profile(name: &str, v: &Value) -> Result<Profile> {
    if !valid_profile(name) {
        return Err("Invalid profile name".into());
    }
    let t = table(
        v,
        &format!("profiles.{name}"),
        Some(&["git", "git_ssh", "github", "env", "unset_env"]),
    )?;
    let git = t.get("git").cloned().unwrap_or_else(empty_table);
    let g = table(
        &git,
        "git",
        Some(&[
            "name",
            "email",
            "signing_key",
            "signing_format",
            "sign_commits",
            "config",
        ]),
    )?;
    if g.contains_key("name") != g.contains_key("email") {
        return Err("git.name and git.email must be provided together".into());
    }
    for k in ["name", "email", "signing_key", "signing_format"] {
        if g.contains_key(k) {
            let s = string(g.get(k), &format!("git.{k}"), true)?;
            if ["name", "email"].contains(&k)
                && (s != s.trim() || s.chars().any(|c| matches!(c, '\r' | '\n' | '<' | '>')))
            {
                return Err(format!(
                    "git.{k} must not contain identity delimiters or surrounding whitespace"
                ));
            }
        }
    }
    if let Some(x) = g.get("signing_format") {
        if !["ssh", "openpgp", "x509"].contains(&x.as_str().unwrap_or("")) {
            return Err("Unsupported git.signing_format".into());
        }
    }
    if g.get("sign_commits").is_some_and(|v| !v.is_bool()) {
        return Err("git.sign_commits must be a boolean".into());
    }
    if let Some(c) = g.get("config") {
        for (k, v) in table(c, "git.config", None)? {
            if !git_key(k) {
                return Err("Invalid Git runtime configuration key".into());
            }
            if let Some(a) = v.as_array() {
                if a.is_empty() {
                    return Err("git.config lists must not be empty".into());
                }
                for x in a {
                    string(Some(x), "git.config value", false)?;
                }
            } else {
                string(Some(v), "git.config value", false)?;
            }
        }
    }
    let ssh = t.get("git_ssh").cloned().unwrap_or_else(empty_table);
    let sh = table(&ssh, "git_ssh", Some(&["identity_file", "identities_only"]))?;
    if !sh.is_empty() {
        string(sh.get("identity_file"), "git_ssh.identity_file", true)?;
        if sh.get("identities_only").is_some_and(|v| !v.is_bool()) {
            return Err("git_ssh.identities_only must be a boolean".into());
        }
    }
    let github = t.get("github").cloned().unwrap_or_else(empty_table);
    let gh = table(
        &github,
        "github",
        Some(&["hostname", "expected_user", "config_dir"]),
    )?;
    if !gh.is_empty() {
        string(gh.get("config_dir"), "github.config_dir", true)?;
        let user = string(gh.get("expected_user"), "github.expected_user", true)?;
        if user.len() > 100
            || !user
                .bytes()
                .next()
                .is_some_and(|b| b.is_ascii_alphanumeric())
            || !user
                .bytes()
                .last()
                .is_some_and(|b| b.is_ascii_alphanumeric())
            || !user
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
        {
            return Err("Invalid github.expected_user".into());
        }
        if let Some(h) = gh.get("hostname") {
            let s = string(Some(h), "github.hostname", true)?;
            if !s.bytes().next().is_some_and(|b| b.is_ascii_alphanumeric())
                || !s
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'.' || b == b'-')
            {
                return Err("Invalid github.hostname".into());
            }
        }
    }
    let ev = t.get("env").cloned().unwrap_or_else(empty_table);
    let mut env = Env::new();
    for (k, v) in table(&ev, "env", None)? {
        valid_env(k, false)?;
        env.insert(
            k.clone(),
            string(Some(v), &format!("env.{k}"), false)?.into(),
        );
    }
    let mut unset = Vec::new();
    if let Some(u) = t.get("unset_env") {
        let a = u
            .as_array()
            .ok_or("unset_env must be an array of environment variable names")?;
        for v in a {
            let k = v
                .as_str()
                .ok_or("unset_env must be an array of environment variable names")?;
            valid_env(k, false)?;
            if !unset.contains(&k.to_string()) {
                unset.push(k.into())
            }
        }
    }
    if unset.iter().any(|k| env.contains_key(k)) {
        return Err("An environment variable cannot be both set and unset".into());
    }
    let semantic: HashSet<&str> = if !sh.is_empty() && !gh.is_empty() {
        ["GIT_SSH_COMMAND", "GH_CONFIG_DIR", "GH_HOST"]
            .into_iter()
            .collect()
    } else if !sh.is_empty() {
        ["GIT_SSH_COMMAND"].into_iter().collect()
    } else if !gh.is_empty() {
        ["GH_CONFIG_DIR", "GH_HOST"].into_iter().collect()
    } else {
        HashSet::new()
    };
    if semantic
        .iter()
        .any(|k| env.contains_key(*k) || unset.contains(&k.to_string()))
    {
        return Err("Generic environment conflicts with semantic configuration".into());
    }
    Ok(Profile {
        name: name.into(),
        git,
        ssh,
        github,
        env,
        unset,
    })
}
fn passwd_home(username: Option<&str>) -> Option<String> {
    use std::ffi::{CStr, CString};
    let user = username.map(CString::new).transpose().ok()?;
    let mut buffer = vec![0u8; 16 * 1024];
    loop {
        let mut record: libc::passwd = unsafe { std::mem::zeroed() };
        let mut result = std::ptr::null_mut();
        let status = unsafe {
            if let Some(ref user) = user {
                libc::getpwnam_r(
                    user.as_ptr(),
                    &mut record,
                    buffer.as_mut_ptr().cast(),
                    buffer.len(),
                    &mut result,
                )
            } else {
                libc::getpwuid_r(
                    libc::getuid(),
                    &mut record,
                    buffer.as_mut_ptr().cast(),
                    buffer.len(),
                    &mut result,
                )
            }
        };
        if status == libc::ERANGE && buffer.len() < 1024 * 1024 {
            buffer.resize(buffer.len() * 2, 0);
            continue;
        }
        if status != 0 || result.is_null() || record.pw_dir.is_null() {
            return None;
        }
        return Some(
            unsafe { CStr::from_ptr(record.pw_dir) }
                .to_string_lossy()
                .into_owned(),
        );
    }
}

pub fn expand(s: &str, env: &Env) -> String {
    if s == "~" || s.starts_with("~/") {
        let home = env
            .get("HOME")
            .cloned()
            .or_else(|| std::env::var("HOME").ok())
            .or_else(|| passwd_home(None));
        return home.map_or_else(|| s.into(), |home| format!("{home}{}", &s[1..]));
    }
    if let Some(tail) = s.strip_prefix('~') {
        let (user, suffix) = tail.split_once('/').map_or((tail, ""), |(a, b)| (a, b));
        if !user.is_empty() {
            if let Some(home) = passwd_home(Some(user)) {
                return if tail.contains('/') {
                    format!("{home}/{suffix}")
                } else {
                    home
                };
            }
        }
    }
    s.into()
}

pub fn config_path(env: &Env) -> PathBuf {
    if let Some(s) = env.get("DEVWHO_CONFIG").filter(|s| !s.is_empty()) {
        return expand(s, env).into();
    }
    let root = env
        .get("XDG_CONFIG_HOME")
        .filter(|s| !s.is_empty())
        .cloned()
        .unwrap_or_else(|| format!("{}/.config", expand("~", env)));
    Path::new(&root).join("devwho/config.toml")
}
pub fn load(path: Option<&str>, env: &Env) -> Result<Config> {
    let raw_path = path
        .map(|s| PathBuf::from(expand(s, env)))
        .unwrap_or_else(|| config_path(env));
    let path = if raw_path.is_absolute() {
        raw_path
    } else {
        std::env::current_dir()
            .map_err(|_| "Cannot resolve configuration path")?
            .join(raw_path)
    };
    let data = fs::read_to_string(&path)
        .map_err(|_| format!("Cannot read configuration: {}", path.display()))?;
    let path = path.canonicalize().unwrap_or(path);
    let v: Value = data.parse().map_err(|_| "Invalid TOML configuration")?;
    let t = table(
        &v,
        "configuration",
        Some(&["version", "settings", "profiles"]),
    )?;
    if t.get("version").and_then(Value::as_integer) != Some(1) {
        return Err("Configuration version must be 1".into());
    }
    let p = t
        .get("profiles")
        .ok_or("Configuration must contain at least one profile")?;
    let pt = table(p, "profiles", None)?;
    if pt.is_empty() {
        return Err("Configuration must contain at least one profile".into());
    }
    let mut profiles = HashMap::new();
    for (k, v) in pt {
        profiles.insert(k.clone(), profile(k, v)?);
    }
    let settings = t.get("settings").cloned().unwrap_or_else(empty_table);
    let st = table(
        &settings,
        "settings",
        Some(&["default_profile", "shortcut_profile", "handoff_warning"]),
    )?;
    let handoff = st
        .get("handoff_warning")
        .map(|v| {
            v.as_bool()
                .ok_or("settings.handoff_warning must be a boolean")
        })
        .transpose()?
        .unwrap_or(false);
    let mut selected = HashMap::new();
    for k in ["default_profile", "shortcut_profile"] {
        let x = st
            .get(k)
            .map(|v| {
                v.as_str()
                    .ok_or(format!("settings.{k} must name an existing profile"))
            })
            .transpose()?;
        if let Some(s) = x {
            if !profiles.contains_key(s) {
                return Err(format!("settings.{k} must name an existing profile"));
            }
        }
        selected.insert(k, x.map(str::to_string));
    }
    Ok(Config {
        path,
        profiles,
        default: selected.remove("default_profile").unwrap(),
        shortcut: selected.remove("shortcut_profile").unwrap(),
        handoff,
    })
}
pub fn current_env() -> Env {
    env::vars().collect()
}

/// Parse the optional dotenv frontend into the same single-profile core model.
pub fn load_env_file(path: &str, selected_name: Option<&str>, env: &Env) -> Result<Config> {
    let raw = PathBuf::from(expand(path, env));
    let path = if raw.is_absolute() {
        raw
    } else {
        std::env::current_dir()
            .map_err(|_| "Cannot resolve environment file path")?
            .join(raw)
    };
    let bytes =
        fs::read(&path).map_err(|_| format!("Cannot read environment file: {}", path.display()))?;
    let text = std::str::from_utf8(&bytes).map_err(|_| "Invalid UTF-8 environment file")?;
    if text.contains('\0')
        || text.as_bytes().windows(2).any(|w| w == b"\r\r")
        || text.replace("\r\n", "").contains('\r')
    {
        return Err("Invalid environment file line ending or NUL".into());
    }
    let mut values = Env::new();
    let mut marker = None;
    for physical in text.split('\n') {
        let line = physical.strip_suffix('\r').unwrap_or(physical);
        let mut line = line.trim_start_matches([' ', '\t']);
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if let Some(x) = line.strip_prefix("export ") {
            line = x;
        }
        let (keypart, rest) = line
            .split_once('=')
            .ok_or("Invalid environment assignment")?;
        let key = keypart.trim_matches([' ', '\t']);
        valid_env(key, key == "DEVWHO_PROFILE")?;
        if values.contains_key(key) || key == "DEVWHO_PROFILE" && marker.is_some() {
            return Err(format!("Duplicate environment key: {key}"));
        }
        let raw = rest.trim_start_matches([' ', '\t']);
        let value = if let Some(tail) = raw.strip_prefix('\'') {
            let pos = tail
                .find('\'')
                .ok_or("Unterminated single-quoted environment value")?;
            let value = &tail[..pos];
            let trailing = tail[pos + 1..].trim_start_matches([' ', '\t']);
            if !trailing.is_empty() && !trailing.starts_with('#') {
                return Err("Unexpected text after environment value".into());
            }
            value.to_string()
        } else if raw.starts_with('"') {
            let mut escaped = false;
            let mut end = None;
            for (i, ch) in raw.char_indices().skip(1) {
                if escaped {
                    escaped = false;
                    continue;
                }
                if ch == '\\' {
                    escaped = true;
                    continue;
                }
                if ch == '"' {
                    end = Some(i);
                    break;
                }
            }
            let end = end.ok_or("Unterminated double-quoted environment value")?;
            let trailing = raw[end + 1..].trim_start_matches([' ', '\t']);
            if !trailing.is_empty() && !trailing.starts_with('#') {
                return Err("Unexpected text after environment value".into());
            }
            serde_json::from_str::<String>(&raw[..=end])
                .map_err(|_| "Invalid JSON-escaped environment value")?
        } else {
            let mut stop = rest.len();
            let chars: Vec<_> = rest.char_indices().collect();
            for (i, (at, ch)) in chars.iter().enumerate() {
                if *ch == '#' && i > 0 && matches!(chars[i - 1].1, ' ' | '\t') {
                    stop = *at;
                    break;
                }
            }
            rest[..stop].trim_matches([' ', '\t']).to_string()
        };
        if value.contains('\0') {
            return Err("Environment value contains NUL".into());
        }
        if key == "DEVWHO_PROFILE" {
            if !valid_profile(&value) {
                return Err("Invalid profile name".into());
            }
            marker = Some(value);
        } else {
            values.insert(key.into(), value);
        }
    }
    let name = match (marker, selected_name) {
        (Some(a), Some(b)) if a != b => {
            return Err("DEVWHO_PROFILE and --env-profile disagree".into())
        }
        (Some(a), _) => a,
        (None, Some(b)) if valid_profile(b) => b.into(),
        (None, Some(_)) => return Err("Invalid profile name".into()),
        (None, None) => return Err("Environment file needs DEVWHO_PROFILE or --env-profile".into()),
    };
    let profile = Profile {
        name: name.clone(),
        git: empty_table(),
        ssh: empty_table(),
        github: empty_table(),
        env: values,
        unset: Vec::new(),
    };
    let path = path.canonicalize().unwrap_or(path);
    Ok(Config {
        path,
        profiles: HashMap::from([(name.clone(), profile)]),
        default: None,
        shortcut: Some(name),
        handoff: false,
    })
}

#[cfg(test)]
mod dotenv_tests {
    use super::*;

    #[test]
    fn whitespace_before_hash_is_comment_but_adjacent_hash_is_literal() {
        let path = std::env::temp_dir().join(format!(
            "devwho-rust-dotenv-comments-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::write(
            &path,
            "DEVWHO_PROFILE=one\nX= #comment\nY=\t#comment\nZ=#literal\n",
        )
        .unwrap();
        let config = load_env_file(path.to_str().unwrap(), None, &Env::new()).unwrap();
        let values = &config.profiles["one"].env;
        assert_eq!(values["X"], "");
        assert_eq!(values["Y"], "");
        assert_eq!(values["Z"], "#literal");
        fs::remove_file(path).unwrap();
    }
}
