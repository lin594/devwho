# Independently maintained compatibility core. jq preserves insertion order via to_entries.
def fail($s): error($s);
def check($b;$s): if $b then . else fail($s) end;
def obj: type == "object";
def str: type == "string" and (contains("\u0000")|not);
def nonempty: str and test("\\S");
def table($allowed): check(obj;"Expected table") | if $allowed == null then . else check((keys-$allowed|length)==0;"Unknown configuration field") end;
def runtimekey: test("^GIT_CONFIG_(COUNT|KEY_[0-9]+|VALUE_[0-9]+)\\z");
def envkey($internal): type == "string" and test("^[A-Za-z_][A-Za-z0-9_]*\\z") and (. as $k | (["BASH_ENV","ENV","BASHOPTS","SHELLOPTS","IFS","CDPATH","ZDOTDIR","PS4","PROMPT_COMMAND","GIT_AUTHOR_NAME","GIT_AUTHOR_EMAIL","GIT_COMMITTER_NAME","GIT_COMMITTER_EMAIL"]|index($k)|not)) and (test("^(__DEVWHO|__devwho)")|not) and ((test("^DEVWHO_")|not) or ($internal and . == "DEVWHO_PROFILE")) and ((test("^GIT_CONFIG_(COUNT$|KEY_|VALUE_)")|not) or ($internal and runtimekey));
def pname: type == "string" and test("^[A-Za-z0-9][A-Za-z0-9_.-]*\\z");
def profile:
 table(["git","git_ssh","github","env","unset_env"])
 | .git = ((if has("git") then .git else {} end) | table(["name","email","signing_key","signing_format","sign_commits","config"]))
 | .git_ssh = ((if has("git_ssh") then .git_ssh else {} end) | table(["identity_file","identities_only"]))
 | .github = ((if has("github") then .github else {} end) | table(["hostname","expected_user","config_dir"]))
 | .env = ((if has("env") then .env else {} end) | table(null)) | .unset_env = (if has("unset_env") then .unset_env else [] end)
 | check((.git|has("name")) == (.git|has("email"));"git.name and git.email must be provided together")
 | check(all(.git|to_entries[]|select(.key|IN("name","email","signing_key","signing_format"));.value|nonempty);"Invalid Git string")
 | check(all(.git|to_entries[]|select(.key|IN("name","email")); .value|test("^[^\\s<>\\r\\n](?:[^<>\\r\\n]*[^\\s<>\\r\\n])?\\z"));"Invalid Git identity")
 | check((.git|has("signing_format")|not) or (.git.signing_format|IN("ssh","openpgp","x509"));"Unsupported git.signing_format")
 | check((.git|has("sign_commits")|not) or (.git.sign_commits|type)=="boolean";"git.sign_commits must be boolean")
 | .git.config = ((if .git|has("config") then .git.config else {} end)|table(null))
 | check(all(.git.config|to_entries[];(.key|test("^[A-Za-z][A-Za-z0-9-]*\\.(?:[^\\n\\r\\u0000]+\\.)?[A-Za-z][A-Za-z0-9-]*\\z")) and (.value|if type=="array" then length>0 and all(.[];str) else str end));"Invalid Git runtime configuration")
 | check((.git_ssh|length)==0 or ((.git_ssh.identity_file|nonempty) and ((.git_ssh|has("identities_only")|not) or (.git_ssh.identities_only|type)=="boolean"));"Invalid git_ssh configuration")
 | check((.github|length)==0 or ((.github.config_dir|nonempty) and (.github.expected_user|type=="string" and test("^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,98}[A-Za-z0-9])?\\z")) and ((.github|has("hostname")|not) or (.github.hostname|type=="string" and test("^[A-Za-z0-9][A-Za-z0-9.-]*\\z"))));"Invalid github configuration")
 | check(all(.env|to_entries[];(.key|envkey(false)) and (.value|str));"Invalid/reserved environment variable or value")
 | check(.unset_env|type=="array" and all(.[];envkey(false));"Invalid unset_env")
 | .unset_env |= reduce .[] as $k ([]; if index($k)==null then .+[$k] else . end)
 | check(((.env|keys) - .unset_env |length)==(.env|length);"Environment variable both set and unset")
 | . as $p | ([if (.git_ssh|length)>0 then "GIT_SSH_COMMAND" else empty end, if (.github|length)>0 then "GH_CONFIG_DIR","GH_HOST" else empty end]) as $semantic
 | check(all($semantic[]; . as $k | (($p.env|has($k)) or ($p.unset_env|index($k)!=null))|not);"Generic environment conflicts with semantic configuration");
def config:
 table(["version","settings","profiles"])
 | check(.version==1;"Configuration version must be 1")
 | .profiles |= table(null) | check((.profiles|length)>0;"Configuration must contain profiles")
 | check(all(.profiles|keys[];pname);"Invalid profile name")
 | .profiles |= with_entries(.value |= profile)
 | .settings = ((if has("settings") then .settings else {} end)|table(["default_profile","shortcut_profile","handoff_warning"]))
 | . as $c | check(all(.settings|to_entries[];if .key=="handoff_warning" then .value|type=="boolean" else .value as $v | ($v|type)=="string" and ($c.profiles|has($v)) end);"Invalid settings");
def pairs:
 . as $env | if has("GIT_CONFIG_COUNT")|not then [] else
 .GIT_CONFIG_COUNT as $n | check($n|type=="string" and test("^[0-9]{1,6}\\z") and (tonumber<=4096);"Invalid GIT_CONFIG_COUNT")
 | [range(0;($n|tonumber)) as $i | [$env["GIT_CONFIG_KEY_\($i)"],$env["GIT_CONFIG_VALUE_\($i)"]]
 | check((.[0]|str and length>0) and (.[1]|str);"Missing/invalid Git runtime variable")] end;
def state:
 if .==null then . else
 table(["version","profile","baseline","managed","runtime"])
 | check((keys|length)==5 and .version==1 and (.profile|pname);"Invalid DevWho shell state")
 | check(.baseline|obj and all(to_entries[];(.key|envkey(true) and (runtimekey|not)) and (.value==null or (.value|str)));"Invalid DevWho baseline")
 | . as $s | check(.managed|type=="array" and all(.[];type=="string" and (. as $k | $s.baseline|has($k))) ;"Invalid DevWho managed variables")
 | check((.managed|unique|length)==(.managed|length) and (.managed|index("DEVWHO_PROFILE")!=null);"Invalid DevWho managed variables")
 | if .runtime==null then . else .runtime |= (table(["baseline","before","owned"])
 | check((keys|length)==3;"Invalid runtime state")
 | check(.baseline|obj and all(to_entries[];(.key|runtimekey) and (.value|str));"Invalid runtime baseline")
 | (.baseline|pairs) as $ignore
 | check(all(.before,.owned;type=="array" and length<=4096 and all(.[];type=="array" and length==2 and (.[0]|str and length>0) and (.[1]|str)));"Invalid runtime pairs")) end end;
def conflicts($p;$e):
 reduce ["GIT_AUTHOR_NAME","GIT_AUTHOR_EMAIL","GIT_COMMITTER_NAME","GIT_COMMITTER_EMAIL"][] as $k (.; check(($e[$k]//"")=="";"Conflicting environment variable: "+$k))
 | if ($p.github|length)>0 then reduce ["GH_TOKEN","GITHUB_TOKEN"][] as $k (.; check(($e[$k]//"")=="" and ($p.env[$k]//"")=="";"Conflicting environment variable: "+$k)) else . end;
def sempath($e):
 if .=="~" or startswith("~/") then check(($e.HOME//"")|startswith("/");"Semantic path requires absolute effective HOME") | $e.HOME + .[1:]
 else check(startswith("/");"Semantic path must be absolute, ~, or start with ~/") end;
def quote: if test("^[A-Za-z0-9_@%+=:,./-]+\\z") then . else "'" + gsub("'"; "'\"'\"'") + "'" end;
def compile($p;$name;$e):
 conflicts($p;$e)
 | ($e | delpaths([$p.unset_env[]|[.]]) | . + $p.env) as $pathenv
 | {values:($p.env+{DEVWHO_PROFILE:$name}),unset:$p.unset_env,
 runtime:([$p.git.config|to_entries[]|.key as $k|.value|if type=="array" then .[] else . end|[$k,.]]
 + [if $p.git|has("name") then ["user","author","committer"][] as $kind | [($kind+".name"),$p.git.name],[($kind+".email"),$p.git.email] else empty end]
 + [if $p.git|has("signing_key") then ["user.signingKey",$p.git.signing_key] else empty end, if $p.git|has("signing_format") then ["gpg.format",$p.git.signing_format] else empty end, if $p.git|has("sign_commits") then ["commit.gpgSign",($p.git.sign_commits|tostring)] else empty end])}
 | if ($p.git_ssh|length)>0 then ($p.git_ssh.identity_file|sempath($pathenv)) as $key | .ssh_file=$key | .values.GIT_SSH_COMMAND=("ssh -i "+($key|quote)+(if $p.git_ssh.identities_only==false then "" else " -o IdentitiesOnly=yes" end)) else . end
 | if ($p.github|length)>0 then .values.GH_CONFIG_DIR=($p.github.config_dir|sempath($pathenv)) | .values.GH_HOST=($p.github.hostname//"github.com") else . end;
def runtime($r;$owned):
 if $r==null and ($owned|length)==0 then {target:.,runtime:null} else
 . as $target | pairs as $current | ($r // {baseline:($target|with_entries(select(.key|runtimekey))),before:$current,owned:[]}) as $r
 | ($r.before|length) as $boundary
 | check($current[:$boundary]==$r.before and $current[$boundary:($boundary+($r.owned|length))]==$r.owned;"Managed Git runtime configuration was changed")
 | ($current[:$boundary]+$current[($boundary+($r.owned|length)):]) as $retained
 | ($retained+$owned) as $desired_pairs | check(($desired_pairs|length)<=4096;"Too many Git runtime entries")
 | ($r.baseline|pairs) as $original
 | ($r.baseline | if ($owned|length)>0 or $retained!=$original then .GIT_CONFIG_COUNT=($desired_pairs|length|tostring) | reduce range(0;($desired_pairs|length)) as $i (.; .["GIT_CONFIG_KEY_\($i)"]=$desired_pairs[$i][0] | .["GIT_CONFIG_VALUE_\($i)"]=$desired_pairs[$i][1]) else . end) as $desired
 | (["GIT_CONFIG_COUNT"]+[range(0;([$current|length,$desired_pairs|length]|max))|"GIT_CONFIG_KEY_\(.)","GIT_CONFIG_VALUE_\(.)"]) as $touched
 | {target:(reduce $touched[] as $k ($target; if $desired|has($k) then .[$k]=$desired[$k] else del(.[$k]) end)),runtime:{baseline:$r.baseline,before:$retained,owned:$owned}} end;
def transition($cfg;$name;$env;$old):
 ($old|state) as $old
 | (if $name==null then null else $cfg.profiles[$name] end) as $p
 | check($name==null or $p!=null;"Unknown profile")
 | if $p!=null then conflicts($p;$env) else . end
 | ($old.baseline//{}) as $baseline
 | (reduce ($old.managed//[])[] as $k ($env; if $baseline[$k]==null then del(.[$k]) else .[$k]=$baseline[$k] end)) as $restored
 | (if $p==null then null else compile($p;$name;$restored) end) as $compiled
 | ($restored|runtime($old.runtime;$compiled.runtime//[])) as $r
 | (($compiled.values//{}|keys)+($compiled.unset//[])|unique) as $managed
 | (reduce $managed[] as $k ($baseline; if has($k) then . else .[$k]=$r.target[$k] end)) as $baseline
 | ($r.target|delpaths([($compiled.unset//[])[]|[.]])|.+($compiled.values//{})) as $target
 | {set:($target|with_entries(select(.key as $k|($env|has($k)|not) or $env[$k]!=.value))),unset:(($env|keys)-($target|keys)),ssh_file:$compiled.ssh_file,state:(if $p==null then null else {version:1,profile:$name,baseline:$baseline,managed:$managed,runtime:$r.runtime} end),target:$target};
def render($shell):
 "if "+([(.set|keys[]),.unset[],"__DEVWHO_STATE"]|unique|map("__devwho_writable "+@sh)|join(" && "))+"; then\n"
 + ([.unset[]|"  unset "+.]|join("\n"))+"\n"
 + ([.set|to_entries|sort_by(.key)[]|"  export "+.key+"="+(.value|@sh)]|join("\n"))+"\n"
 + "  __DEVWHO_STATE="+((if .state==null then "" else .state|tojson end)|@sh)+"\n  "
 + (if $shell=="bash" then "export -n __DEVWHO_STATE" else "typeset -g +x __DEVWHO_STATE" end)+"\nelse\n  return 1\nfi\n";
