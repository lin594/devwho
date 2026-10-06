mod config;
mod engine;
mod shell;
use config::{Config, Env, Result};
use std::{
    env,
    fs::{self, OpenOptions},
    io::{self, Read, Write},
    os::unix::{
        fs::{DirBuilderExt, OpenOptionsExt},
        process::CommandExt,
    },
    path::PathBuf,
    process::{Command, ExitCode},
};
fn run_timeout(args: &[&str], seconds: u64) -> Option<(i32, String)> {
    use std::{
        process::Stdio,
        sync::mpsc,
        thread,
        time::{Duration, Instant},
    };
    let mut child = Command::new(args[0])
        .args(&args[1..])
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .ok()?;
    let mut stdout = child.stdout.take()?;
    let (sender, receiver) = mpsc::channel();
    thread::spawn(move || {
        let mut result = Vec::new();
        let mut buffer = [0u8; 8192];
        loop {
            let n = stdout.read(&mut buffer).unwrap_or(0);
            if n == 0 {
                break;
            }
            if result.len() < 1024 * 1024 {
                let amount = n.min(1024 * 1024 - result.len());
                result.extend_from_slice(&buffer[..amount]);
            }
        }
        let _ = sender.send(result);
    });
    let start = Instant::now();
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) if start.elapsed() < Duration::from_secs(seconds) => {
                thread::sleep(Duration::from_millis(20))
            }
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                return None;
            }
        }
    };
    let output = receiver.recv_timeout(Duration::from_millis(200)).ok()?;
    Some((
        status.code().unwrap_or(1),
        String::from_utf8_lossy(&output).into_owned(),
    ))
}
fn run(args: &[&str]) -> Option<(i32, String)> {
    run_timeout(args, 10)
}
fn help() {
    println!("Per-shell developer identity through environment variables.\n\nUsage: devwho [--config PATH] COMMAND\n\nCommands: list, show PROFILE, current [--verbose], doctor [PROFILE] [--offline], exec PROFILE -- COMMAND, config path|init, init bash|zsh");
}
fn ident(value: &str) -> Option<String> {
    let s = value.trim();
    let (identity, rest) = s.rsplit_once('>')?;
    if !identity.contains('<') || identity.chars().any(|c| c == '\r' || c == '\n') {
        return None;
    }
    let rest = rest.trim();
    let mut x = rest.split(' ');
    if x.next()?.bytes().all(|b| b.is_ascii_digit())
        && x.next().is_some_and(|v| {
            v.len() == 5
                && (v.starts_with('+') || v.starts_with('-'))
                && v[1..].bytes().all(|b| b.is_ascii_digit())
        })
        && x.next().is_none()
    {
        Some(format!("{identity}>"))
    } else {
        None
    }
}
fn git_null_values(output: &str) -> Vec<&str> {
    output
        .strip_suffix('\0')
        .unwrap_or(output)
        .split('\0')
        .collect()
}

fn doctor(c: &Config, name: Option<&str>, offline: bool, e: &Env) -> Result<i32> {
    let name = name.or_else(|| e.get("DEVWHO_PROFILE").map(String::as_str));
    let Some(name) = name else {
        println!("FAIL: no active profile; use setdev PROFILE or name a profile to diagnose");
        return Ok(1);
    };
    let p = c
        .profiles
        .get(name)
        .ok_or(format!("Unknown profile \"{name}\"; run devwho list"))?;
    println!("Profile: {name}");
    let mut fail = false;
    let mut unverified = false;
    let mut report = |label: &str, status: &str, detail: &str| {
        println!(
            "{label}: {status}{}",
            if detail.is_empty() {
                String::new()
            } else {
                format!(" — {detail}")
            }
        );
        fail |= status == "FAIL";
        unverified |= status == "UNVERIFIED";
    };
    report(
        "Context",
        if e.get("DEVWHO_PROFILE").is_some_and(|x| x == name) {
            "OK"
        } else {
            "FAIL"
        },
        "metadata is not proof of authentication",
    );
    let desired = match engine::compile(p, e) {
        Ok(x) => x,
        Err(x) => {
            report("Configuration/environment", "FAIL", &x);
            return Ok(1);
        }
    };
    let g = p.git.as_table().unwrap();
    if let Some(n) = g.get("name") {
        let expected = format!("{} <{}>", n.as_str().unwrap(), g["email"].as_str().unwrap());
        for (label, var) in [
            ("Git author", "GIT_AUTHOR_IDENT"),
            ("Git committer", "GIT_COMMITTER_IDENT"),
        ] {
            match run(&["git", "var", var]) {
                Some((0, out)) => {
                    let actual = ident(&out);
                    if actual.as_deref() == Some(&expected) {
                        report(label, "OK", &expected)
                    } else {
                        report(
                            label,
                            "FAIL",
                            &format!(
                                "expected {expected}; actual {}",
                                actual.unwrap_or("unrecognized identity output".into())
                            ),
                        )
                    }
                }
                Some(_) => report(
                    label,
                    "UNVERIFIED",
                    "Git cannot resolve identity in this context",
                ),
                None => report(label, "UNVERIFIED", "Git unavailable or timed out"),
            }
        }
    }
    let mut groups = std::collections::BTreeMap::<String, Vec<String>>::new();
    for [k, v] in &desired.runtime {
        groups.entry(k.clone()).or_default().push(v.clone())
    }
    let mut mismatch = false;
    let mut unavailable = false;
    for (k, values) in &groups {
        match run(&["git", "config", "--null", "--get-all", k]) {
            Some((rc, out)) => {
                let actual: Vec<&str> = git_null_values(&out);
                if rc != 0
                    || actual.len() < values.len()
                    || actual[actual.len() - values.len()..]
                        != values.iter().map(String::as_str).collect::<Vec<_>>()
                {
                    mismatch = true
                }
            }
            None => unavailable = true,
        }
    }
    if !groups.is_empty() {
        report(
            "Git runtime configuration",
            if mismatch {
                "FAIL"
            } else if unavailable {
                "UNVERIFIED"
            } else {
                "OK"
            },
            "values hidden",
        )
    }
    if p.ssh.as_table().is_some_and(|t| !t.is_empty()) {
        report(
            "Git SSH command",
            if e.get("GIT_SSH_COMMAND") == desired.values.get("GIT_SSH_COMMAND") {
                "OK"
            } else {
                "FAIL"
            },
            "local command/key check only; remote authentication is unverified",
        )
    }
    for (k, v) in &p.env {
        report(
            &format!("Environment {k}"),
            if e.get(k) == Some(v) { "OK" } else { "FAIL" },
            "value hidden",
        )
    }
    for k in &p.unset {
        report(
            &format!("Unset {k}"),
            if e.contains_key(k) { "FAIL" } else { "OK" },
            "",
        )
    }
    if let Some(gh) = p.github.as_table().filter(|x| !x.is_empty()) {
        let expected = gh["expected_user"].as_str().unwrap();
        report(
            "GitHub config directory",
            if e.get("GH_CONFIG_DIR") == desired.values.get("GH_CONFIG_DIR") {
                "OK"
            } else {
                "FAIL"
            },
            "",
        );
        report(
            "GitHub hostname",
            if e.get("GH_HOST") == desired.values.get("GH_HOST") {
                "OK"
            } else {
                "FAIL"
            },
            "",
        );
        if offline {
            report(
                "GitHub identity",
                "UNVERIFIED",
                &format!("offline mode; expected {expected}"),
            )
        } else {
            let host = gh
                .get("hostname")
                .and_then(|v| v.as_str())
                .unwrap_or("github.com");
            match run_timeout(
                &["gh", "api", "--hostname", host, "user", "--jq", ".login"],
                15,
            ) {
                Some((0, out)) => {
                    let actual = out.trim();
                    if actual.len() > 100
                        || actual.is_empty()
                        || !actual
                            .bytes()
                            .all(|b| b.is_ascii_alphanumeric() || b"_.-".contains(&b))
                    {
                        report(
                            "GitHub identity",
                            "UNVERIFIED",
                            &format!("API/login unavailable; expected {expected}"),
                        )
                    } else {
                        report(
                            "GitHub identity",
                            if actual == expected { "OK" } else { "FAIL" },
                            &format!("expected {expected}; actual {actual}"),
                        )
                    }
                }
                _ => report(
                    "GitHub identity",
                    "UNVERIFIED",
                    &format!("API/login unavailable; expected {expected}"),
                ),
            }
        }
    }
    Ok(if fail {
        1
    } else if unverified {
        2
    } else {
        0
    })
}
fn main_run() -> Result<i32> {
    let args: Vec<String> = env::args().skip(1).collect();
    let mut i = 0;
    let mut explicit = None;
    let mut env_file = None;
    let mut env_profile = None;
    while i < args.len() {
        match args[i].as_str() {
            "--config" => {
                i += 1;
                explicit = Some(args.get(i).ok_or("--config requires PATH")?.clone());
                i += 1
            }
            "--env-file" => {
                i += 1;
                env_file = Some(args.get(i).ok_or("--env-file requires PATH")?.clone());
                i += 1
            }
            "--env-profile" => {
                i += 1;
                env_profile = Some(args.get(i).ok_or("--env-profile requires NAME")?.clone());
                i += 1
            }
            "--help" | "-h" => {
                help();
                return Ok(0);
            }
            "--version" => {
                println!("devwho 0.1.0");
                return Ok(0);
            }
            _ => break,
        }
    }
    if explicit.is_some() && env_file.is_some() {
        return Err("--config and --env-file are mutually exclusive".into());
    }
    if env_profile.is_some() && env_file.is_none() {
        return Err("--env-profile requires --env-file".into());
    }
    let cmd = args
        .get(i)
        .map(String::as_str)
        .ok_or("a command is required")?;
    let rest = &args[i + 1..];
    let e = config::current_env();
    if cmd == "current" {
        if rest.iter().any(|x| x != "--verbose") {
            return Err("invalid current option".into());
        }
        println!(
            "{}",
            e.get("DEVWHO_PROFILE")
                .filter(|x| !x.is_empty())
                .map(String::as_str)
                .unwrap_or("none")
        );
        if rest.contains(&"--verbose".into()) {
            println!(
                "Configuration: {}",
                explicit
                    .clone()
                    .or_else(|| env_file.clone())
                    .unwrap_or_else(|| config::config_path(&e).display().to_string())
            );
            println!(
                "GitHub config directory: {}",
                e.get("GH_CONFIG_DIR")
                    .map(String::as_str)
                    .unwrap_or("default")
            );
            println!(
                "GitHub hostname: {}",
                e.get("GH_HOST").map(String::as_str).unwrap_or("github.com")
            );
            for (label, var) in [
                ("Git author", "GIT_AUTHOR_IDENT"),
                ("Git committer", "GIT_COMMITTER_IDENT"),
            ] {
                let id =
                    run(&["git", "var", var])
                        .and_then(|(rc, out)| if rc == 0 { ident(&out) } else { None });
                println!("{label}: {}", id.as_deref().unwrap_or("unavailable"))
            }
            println!("Use devwho doctor to verify actual tool identity.")
        }
        return Ok(0);
    }
    if cmd == "config" {
        let path = explicit
            .as_ref()
            .or(env_file.as_ref())
            .map(|s| PathBuf::from(config::expand(s, &e)))
            .unwrap_or_else(|| config::config_path(&e));
        match rest.first().map(String::as_str) {
            Some("path") => {
                println!("{}", path.display());
                return Ok(0);
            }
            Some("init") => {
                if env_file.is_some() {
                    return Err("config init is unavailable for --env-file".into());
                }
                if let Some(parent) = path.parent() {
                    fs::DirBuilder::new()
                        .recursive(true)
                        .mode(0o700)
                        .create(parent)
                        .map_err(|_| "local operation failed (OSError)")?
                }
                let mut file = OpenOptions::new()
                    .write(true)
                    .create_new(true)
                    .mode(0o600)
                    .open(&path)
                    .map_err(|_| "local operation failed (OSError)")?;
                file.write_all(b"version = 1\n\n[profiles.personal.git]\nname = \"Jane Doe\"\nemail = \"jane@example.com\"\n\n[profiles.work.git]\nname = \"Jane Doe\"\nemail = \"jane@company.example\"\n").map_err(|_|"local operation failed (OSError)")?;
                println!(
                    "Created {}; edit its example identities before use.",
                    path.display()
                );
                return Ok(0);
            }
            Some("export-env") => {
                let name = rest.get(1).ok_or("config export-env needs PROFILE")?;
                let source = if let Some(path) = env_file.as_deref() {
                    config::load_env_file(path, env_profile.as_deref(), &e)?
                } else {
                    config::load(explicit.as_deref(), &e)?
                };
                let p = source
                    .profiles
                    .get(name)
                    .ok_or(format!("Unknown profile \"{name}\"; run devwho list"))?;
                if !p.git.as_table().unwrap().is_empty()
                    || !p.ssh.as_table().unwrap().is_empty()
                    || !p.github.as_table().unwrap().is_empty()
                    || !p.unset.is_empty()
                {
                    return Err(
                        "Profile has semantic settings or unsets and cannot be exported to dotenv"
                            .into(),
                    );
                }
                println!("DEVWHO_PROFILE={}", serde_json::to_string(name).unwrap());
                for (k, v) in &p.env {
                    println!("{k}={}", serde_json::to_string(v).unwrap())
                }
                return Ok(0);
            }
            _ => return Err("config needs path, init, or export-env".into()),
        }
    }
    let c = if let Some(path) = env_file.as_deref() {
        config::load_env_file(path, env_profile.as_deref(), &e)?
    } else {
        config::load(explicit.as_deref(), &e)?
    };
    match cmd {
        "list" => {
            let mut keys: Vec<_> = c.profiles.keys().collect();
            keys.sort();
            for k in keys {
                println!("{k}")
            }
            Ok(0)
        }
        "show" => {
            let name = rest.first().ok_or("show needs PROFILE")?;
            let p = c
                .profiles
                .get(name)
                .ok_or(format!("Unknown profile \"{name}\"; run devwho list"))?;
            println!("Profile: {}", p.name);
            let g = p.git.as_table().unwrap();
            if let Some(n) = g.get("name") {
                println!(
                    "Git: {} <{}>",
                    n.as_str().unwrap(),
                    g["email"].as_str().unwrap()
                )
            }
            if let Some(s) = p.ssh.as_table().filter(|x| !x.is_empty()) {
                println!("Git SSH key: {}", s["identity_file"].as_str().unwrap())
            }
            if let Some(s) = p.github.as_table().filter(|x| !x.is_empty()) {
                println!(
                    "GitHub expected user: {}",
                    s["expected_user"].as_str().unwrap()
                );
                println!("GitHub config: {}", s["config_dir"].as_str().unwrap())
            }
            println!(
                "Custom environment keys: {}",
                p.env.keys().cloned().collect::<Vec<_>>().join(", ")
            );
            println!("Unset keys: {}", p.unset.join(", "));
            Ok(0)
        }
        "doctor" => {
            let offline = rest.contains(&"--offline".into());
            let name = rest.iter().find(|x| *x != "--offline").map(String::as_str);
            doctor(&c, name, offline, &e)
        }
        "init" => {
            let sh = rest
                .first()
                .map(String::as_str)
                .ok_or("init needs bash or zsh")?;
            if sh != "bash" && sh != "zsh" {
                return Err("init needs bash or zsh".into());
            }
            if let Some(d) = &c.default {
                if e.get("DEVWHO_PROFILE").map_or(true, |x| x.is_empty()) {
                    engine::compile(&c.profiles[d], &e)?;
                }
            }
            print!(
                "{}",
                shell::init(
                    sh,
                    &c.path,
                    c.default.is_some(),
                    env_file.as_ref().and(c.shortcut.as_deref())
                )
            );
            Ok(0)
        }
        "exec" => {
            let name = rest.first().ok_or("exec needs PROFILE")?;
            let child = rest.get(1..).unwrap_or(&[]);
            let child = if child.first().is_some_and(|x| x == "--") {
                &child[1..]
            } else {
                child
            };
            if child.is_empty() {
                return Err("devwho exec needs a command after --".into());
            }
            if !c.profiles.contains_key(name) {
                return Err(format!("Unknown profile \"{name}\"; run devwho list"));
            }
            let (p, _) = engine::transition(&c, Some(name), &e, None)?;
            let env = p.apply(&e);
            let mut command = Command::new(&child[0]);
            command.args(&child[1..]).env_clear().envs(env);
            let err = command.exec();
            match err.kind() {
                io::ErrorKind::NotFound => {
                    eprintln!("devwho: command not found");
                    Ok(127)
                }
                io::ErrorKind::PermissionDenied => {
                    eprintln!("devwho: command is not executable");
                    Ok(126)
                }
                _ => Err("local operation failed (OSError)".into()),
            }
        }
        "internal" => internal(&c, rest, &e),
        _ => Err("unknown command".into()),
    }
}
fn internal(c: &Config, rest: &[String], e: &Env) -> Result<i32> {
    let action = rest
        .first()
        .map(String::as_str)
        .ok_or("internal action required")?;
    if action == "notice" {
        if c.handoff {
            match run_timeout(&["git","status","--porcelain","--untracked-files=normal"],2){Some((0,out))if !out.is_empty()=>eprintln!("devwho: this repository has uncommitted changes; confirm the handoff before editing or committing. Switching identity does not assign those changes."),None=>eprintln!("devwho: handoff check unavailable; check git status before taking over."),_=>()}
        }
        return Ok(0);
    }
    let sh = rest
        .windows(2)
        .find(|x| x[0] == "--shell")
        .map(|x| x[1].as_str())
        .ok_or("internal transition requires a shell")?;
    if sh != "bash" && sh != "zsh" {
        return Err("internal transition requires a shell".into());
    }
    if action == "bootstrap" {
        if let Some(d) = &c.default {
            let (p, _) = engine::transition(c, Some(d), e, None)?;
            print!("{}", shell::patch(&p, None, sh))
        }
        return Ok(0);
    }
    if action != "transition" {
        return Err("invalid internal action".into());
    }
    let mut raw = Vec::new();
    io::stdin()
        .take(1024 * 1024 + 1)
        .read_to_end(&mut raw)
        .map_err(|_| "Invalid DevWho shell state")?;
    if raw.len() > 1024 * 1024 {
        return Err("DevWho shell state exceeds its size limit".into());
    }
    let state = if raw.is_empty() {
        None
    } else {
        Some(
            serde_json::from_slice::<engine::State>(&raw)
                .map_err(|_| "Invalid DevWho shell state; open a fresh shell")?,
        )
    };
    let restore = rest.contains(&"--restore".into());
    let activate = rest
        .iter()
        .position(|x| x == "--activate")
        .and_then(|i| rest.get(i + 1))
        .filter(|x| !x.starts_with("--"))
        .map(String::as_str);
    let name = if restore {
        None
    } else {
        activate.or(c.shortcut.as_deref())
    };
    if !restore && name.is_none() {
        return Err("setdev needs PROFILE or settings.shortcut_profile".into());
    }
    if let Some(n) = name {
        if !c.profiles.contains_key(n) {
            return Err(format!("Unknown profile \"{n}\"; run devwho list"));
        }
    }
    let (p, s) = engine::transition(c, name, e, state)?;
    print!("{}", shell::patch(&p, s.as_ref(), sh));
    Ok(0)
}
fn main() -> ExitCode {
    match main_run() {
        Ok(n) => ExitCode::from(n as u8),
        Err(e) => {
            eprintln!("devwho: {e}");
            ExitCode::from(1)
        }
    }
}

#[cfg(test)]
mod doctor_tests {
    use super::git_null_values;

    #[test]
    fn runtime_null_output_preserves_trailing_empty_value() {
        assert_eq!(git_null_values("helper\0\0"), vec!["helper", ""]);
        assert_eq!(git_null_values("\0"), vec![""]);
    }
}
