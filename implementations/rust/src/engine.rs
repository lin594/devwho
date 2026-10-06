use crate::config::{is_runtime, valid_env, Config, Env, Profile, Result};
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path,
};
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct State {
    pub version: i64,
    pub profile: String,
    pub baseline: BTreeMap<String, Option<String>>,
    pub managed: Vec<String>,
    pub runtime: Option<Runtime>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Runtime {
    pub baseline: Env,
    pub before: Vec<[String; 2]>,
    pub owned: Vec<[String; 2]>,
}
#[derive(Clone, Debug)]
pub struct Compiled {
    pub values: Env,
    pub unset: Vec<String>,
    pub runtime: Vec<[String; 2]>,
}
#[derive(Clone, Debug)]
pub struct Patch {
    pub set: Env,
    pub unset: Vec<String>,
}
impl Patch {
    pub fn apply(&self, env: &Env) -> Env {
        let mut e = env.clone();
        for k in &self.unset {
            e.remove(k);
        }
        e.extend(self.set.clone());
        e
    }
}
fn conflicts(p: &Profile, e: &Env) -> Result<()> {
    for k in [
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    ] {
        if e.get(k).is_some_and(|s| !s.is_empty()) {
            return Err(format!("Conflicting environment variable: {k}"));
        }
    }
    if p.github.as_table().is_some_and(|t| !t.is_empty()) {
        for k in ["GH_TOKEN", "GITHUB_TOKEN"] {
            if e.get(k).is_some_and(|s| !s.is_empty())
                || p.env.get(k).is_some_and(|s| !s.is_empty())
            {
                return Err(format!("Conflicting environment variable: {k}"));
            }
        }
    }
    Ok(())
}
fn semantic_path(v: &str, e: &Env, field: &str) -> Result<String> {
    let p = if v == "~" || v.starts_with("~/") {
        let home = e.get("HOME").filter(|s| !s.is_empty()).ok_or(format!(
            "{field} requires a nonempty effective HOME for ~ paths"
        ))?;
        format!("{home}{}", &v[1..])
    } else {
        v.into()
    };
    if !Path::new(&p).is_absolute() {
        return Err(format!(
            "{field} must be an absolute path, ~, or start with ~/"
        ));
    }
    Ok(p)
}
fn quote(s: &str) -> String {
    if s.is_empty() {
        return "''".into();
    }
    if s.bytes()
        .all(|b| b.is_ascii_alphanumeric() || b"_@%+=:,./-".contains(&b))
    {
        return s.into();
    }
    format!("'{}'", s.replace('\'', "'\\''"))
}
pub fn compile(p: &Profile, e: &Env) -> Result<Compiled> {
    conflicts(p, e)?;
    let mut values = p.env.clone();
    values.insert("DEVWHO_PROFILE".into(), p.name.clone());
    let mut runtime = Vec::new();
    let g = p.git.as_table().unwrap();
    if let Some(c) = g.get("config").and_then(|v| v.as_table()) {
        for (k, v) in c {
            if let Some(a) = v.as_array() {
                for x in a {
                    runtime.push([k.clone(), x.as_str().unwrap().into()]);
                }
            } else {
                runtime.push([k.clone(), v.as_str().unwrap().into()]);
            }
        }
    }
    if let Some(name) = g.get("name").and_then(|x| x.as_str()) {
        let email = g.get("email").and_then(|x| x.as_str()).unwrap();
        for kind in ["user", "author", "committer"] {
            runtime.push([format!("{kind}.name"), name.into()]);
            runtime.push([format!("{kind}.email"), email.into()]);
        }
    }
    for (field, key) in [
        ("signing_key", "user.signingKey"),
        ("signing_format", "gpg.format"),
    ] {
        if let Some(s) = g.get(field).and_then(|x| x.as_str()) {
            runtime.push([key.into(), s.into()]);
        }
    }
    if let Some(b) = g.get("sign_commits").and_then(|x| x.as_bool()) {
        runtime.push(["commit.gpgSign".into(), b.to_string()]);
    }
    let mut pathenv = e.clone();
    for k in &p.unset {
        pathenv.remove(k);
    }
    pathenv.extend(p.env.clone());
    if let Some(s) = p.ssh.as_table().filter(|s| !s.is_empty()) {
        let identity = semantic_path(
            s["identity_file"].as_str().unwrap(),
            &pathenv,
            "git_ssh.identity_file",
        )?;
        if !Path::new(&identity).is_file() {
            return Err("git_ssh.identity_file must identify an existing file".into());
        }
        let mut command = format!("ssh -i {}", quote(&identity));
        if s.get("identities_only")
            .and_then(|x| x.as_bool())
            .unwrap_or(true)
        {
            command.push_str(" -o IdentitiesOnly=yes");
        }
        values.insert("GIT_SSH_COMMAND".into(), command);
    }
    if let Some(gh) = p.github.as_table().filter(|s| !s.is_empty()) {
        values.insert(
            "GH_CONFIG_DIR".into(),
            semantic_path(
                gh["config_dir"].as_str().unwrap(),
                &pathenv,
                "github.config_dir",
            )?,
        );
        values.insert(
            "GH_HOST".into(),
            gh.get("hostname")
                .and_then(|x| x.as_str())
                .unwrap_or("github.com")
                .into(),
        );
    }
    for (k, v) in &values {
        valid_env(k, true)?;
        if v.contains('\0') {
            return Err(format!("Invalid environment value: {k}"));
        }
    }
    Ok(Compiled {
        values,
        unset: p.unset.clone(),
        runtime,
    })
}
fn pairs(e: &Env) -> Result<Vec<[String; 2]>> {
    let Some(count) = e.get("GIT_CONFIG_COUNT") else {
        return Ok(Vec::new());
    };
    if count.len() > 6 || count.is_empty() || !count.bytes().all(|b| b.is_ascii_digit()) {
        return Err("Invalid GIT_CONFIG_COUNT".into());
    }
    let n: usize = count.parse().map_err(|_| "Invalid GIT_CONFIG_COUNT")?;
    if n > 4096 {
        return Err("Invalid GIT_CONFIG_COUNT".into());
    }
    let mut out = Vec::new();
    for i in 0..n {
        let (k, v) = (
            format!("GIT_CONFIG_KEY_{i}"),
            format!("GIT_CONFIG_VALUE_{i}"),
        );
        let a = e.get(&k).ok_or(format!(
            "Missing runtime configuration variable at index {i}"
        ))?;
        let b = e.get(&v).ok_or(format!(
            "Missing runtime configuration variable at index {i}"
        ))?;
        if a.is_empty() || a.contains('\0') || b.contains('\0') {
            return Err(format!(
                "Invalid runtime configuration variable at index {i}"
            ));
        }
        out.push([a.clone(), b.clone()]);
    }
    Ok(out)
}
pub fn validate_state(s: &State) -> Result<()> {
    if s.version != 1 {
        return Err("Unsupported DevWho shell state".into());
    }
    let mut ch = s.profile.chars();
    if !matches!(ch.next(),Some(x) if x.is_ascii_alphanumeric())
        || !ch.all(|x| x.is_ascii_alphanumeric() || "_.-".contains(x))
    {
        return Err("Invalid DevWho shell state".into());
    }
    for (k, v) in &s.baseline {
        valid_env(k, true)?;
        if is_runtime(k) || v.as_ref().is_some_and(|v| v.contains('\0')) {
            return Err("Invalid DevWho baseline".into());
        }
    }
    let unique: BTreeSet<_> = s.managed.iter().collect();
    if unique.len() != s.managed.len()
        || !s.managed.contains(&"DEVWHO_PROFILE".into())
        || s.managed.iter().any(|k| !s.baseline.contains_key(k))
    {
        return Err("Invalid DevWho managed variables".into());
    }
    if let Some(r) = &s.runtime {
        for (k, v) in &r.baseline {
            if !is_runtime(k) || v.contains('\0') {
                return Err("Invalid DevWho runtime baseline".into());
            }
        }
        pairs(&r.baseline)?;
        for entries in [&r.before, &r.owned] {
            if entries.len() > 4096
                || entries
                    .iter()
                    .any(|p| p[0].is_empty() || p.iter().any(|v| v.contains('\0')))
            {
                return Err("Invalid DevWho runtime pairs".into());
            }
        }
    }
    Ok(())
}
fn runtime_transition(
    target: &mut Env,
    r: Option<Runtime>,
    owned: &[[String; 2]],
) -> Result<Option<Runtime>> {
    if r.is_none() && owned.is_empty() {
        return Ok(None);
    }
    let current = pairs(target)?;
    let mut r = if let Some(x) = r {
        x
    } else {
        Runtime {
            baseline: target
                .iter()
                .filter(|(k, _)| is_runtime(k))
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect(),
            before: current.clone(),
            owned: Vec::new(),
        }
    };
    let boundary = r.before.len();
    if current.get(..boundary) != Some(r.before.as_slice())
        || current.get(boundary..boundary + r.owned.len()) != Some(r.owned.as_slice())
    {
        return Err("Managed Git runtime configuration was changed; refusing to remove unrelated configuration".into());
    }
    let mut retained = current[..boundary].to_vec();
    retained.extend_from_slice(&current[boundary + r.owned.len()..]);
    let mut desired_pairs = retained.clone();
    desired_pairs.extend_from_slice(owned);
    if desired_pairs.len() > 4096 {
        return Err("Too many Git runtime configuration entries".into());
    }
    let mut desired = r.baseline.clone();
    let original = pairs(&r.baseline)?;
    if !owned.is_empty() || retained != original {
        desired.insert("GIT_CONFIG_COUNT".into(), desired_pairs.len().to_string());
        for (i, p) in desired_pairs.iter().enumerate() {
            desired.insert(format!("GIT_CONFIG_KEY_{i}"), p[0].clone());
            desired.insert(format!("GIT_CONFIG_VALUE_{i}"), p[1].clone());
        }
    }
    let end = current.len().max(desired_pairs.len());
    for k in std::iter::once("GIT_CONFIG_COUNT".to_string()).chain((0..end).flat_map(|i| {
        [
            format!("GIT_CONFIG_KEY_{i}"),
            format!("GIT_CONFIG_VALUE_{i}"),
        ]
    })) {
        if let Some(v) = desired.get(&k) {
            target.insert(k, v.clone());
        } else {
            target.remove(&k);
        }
    }
    r.before = retained;
    r.owned = owned.into();
    Ok(Some(r))
}
pub fn transition(
    config: &Config,
    name: Option<&str>,
    env: &Env,
    state: Option<State>,
) -> Result<(Patch, Option<State>)> {
    if let Some(s) = &state {
        validate_state(s)?
    }
    let p = name
        .map(|n| config.profiles.get(n).ok_or("Unknown profile"))
        .transpose()?;
    if let Some(p) = p {
        conflicts(p, env)?
    }
    let mut target = env.clone();
    let mut baseline = state
        .as_ref()
        .map(|s| s.baseline.clone())
        .unwrap_or_default();
    if let Some(s) = &state {
        for k in &s.managed {
            if let Some(Some(v)) = baseline.get(k) {
                target.insert(k.clone(), v.clone());
            } else {
                target.remove(k);
            }
        }
    }
    let compiled = p.map(|p| compile(p, &target)).transpose()?;
    let runtime = runtime_transition(
        &mut target,
        state.and_then(|s| s.runtime),
        compiled
            .as_ref()
            .map(|c| c.runtime.as_slice())
            .unwrap_or(&[]),
    )?;
    let mut newstate = None;
    if let Some(c) = compiled {
        let managed: BTreeSet<String> = c
            .values
            .keys()
            .cloned()
            .chain(c.unset.iter().cloned())
            .collect();
        for k in &managed {
            baseline
                .entry(k.clone())
                .or_insert_with(|| target.get(k).cloned());
        }
        for k in c.unset {
            target.remove(&k);
        }
        target.extend(c.values);
        newstate = Some(State {
            version: 1,
            profile: name.unwrap().into(),
            baseline,
            managed: managed.into_iter().collect(),
            runtime,
        });
    }
    let set = target
        .iter()
        .filter(|(k, v)| env.get(*k) != Some(*v))
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect();
    let unset = env
        .keys()
        .filter(|k| !target.contains_key(*k))
        .cloned()
        .collect();
    Ok((Patch { set, unset }, newstate))
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::config;
    use std::{
        fs,
        path::PathBuf,
        sync::atomic::{AtomicUsize, Ordering},
    };
    static FIXTURE_ID: AtomicUsize = AtomicUsize::new(0);
    fn fixture() -> (Config, PathBuf) {
        let dir = std::env::temp_dir().join(format!(
            "devwho-rust-test-{}-{}",
            std::process::id(),
            FIXTURE_ID.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&dir).unwrap();
        let path = dir.join("config.toml");
        fs::write(&path,"version=1\n[profiles.a.git]\nname='Alpha'\nemail='a@example.invalid'\n[profiles.a.env]\nA='yes'\n[profiles.b.git]\nname='Beta'\nemail='b@example.invalid'\n[profiles.b.env]\nB='yes'\n").unwrap();
        let c = config::load(Some(path.to_str().unwrap()), &Env::new()).unwrap();
        (c, dir)
    }
    #[test]
    fn lifecycle_restores_absent_and_empty() {
        let (c, dir) = fixture();
        let mut base = Env::new();
        base.insert("B".into(), String::new());
        let (p, s) = transition(&c, Some("a"), &base, None).unwrap();
        let after = p.apply(&base);
        assert_eq!(after["A"], "yes");
        let (p, s) = transition(&c, Some("b"), &after, s).unwrap();
        let after = p.apply(&after);
        assert!(!after.contains_key("A"));
        assert_eq!(after["B"], "yes");
        let (p, s) = transition(&c, None, &after, s).unwrap();
        assert!(s.is_none());
        assert_eq!(p.apply(&after), base);
        fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn append_preserved_and_tamper_rejected() {
        let (c, dir) = fixture();
        let mut base = Env::new();
        base.insert("GIT_CONFIG_COUNT".into(), "1".into());
        base.insert("GIT_CONFIG_KEY_0".into(), "http.proxy".into());
        base.insert("GIT_CONFIG_VALUE_0".into(), "proxy".into());
        let (p, s) = transition(&c, Some("a"), &base, None).unwrap();
        let mut active = p.apply(&base);
        let n: usize = active["GIT_CONFIG_COUNT"].parse().unwrap();
        active.insert(format!("GIT_CONFIG_KEY_{n}"), "http.sslVerify".into());
        active.insert(format!("GIT_CONFIG_VALUE_{n}"), "true".into());
        active.insert("GIT_CONFIG_COUNT".into(), (n + 1).to_string());
        let (p, _) = transition(&c, None, &active, s.clone()).unwrap();
        let result = p.apply(&active);
        assert_eq!(result["GIT_CONFIG_KEY_1"], "http.sslVerify");
        let mut tampered = active;
        tampered.insert("GIT_CONFIG_VALUE_1".into(), "evil".into());
        assert!(transition(&c, None, &tampered, s).is_err());
        fs::remove_dir_all(dir).unwrap();
    }
}
