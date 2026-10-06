#!/usr/bin/perl
# Environment/argv transport only. The core already validated and calculated it.
use strict;use warnings;use JSON::PP;use File::Path qw(remove_tree);
use Encode qw(encode);
use Errno qw(ENOENT EACCES ENOEXEC);
my($path,$directory)=splice @ARGV,0,2;
my $env=eval {open my $fh,'<:raw',$path or die 'read';local $/;decode_json(<$fh>)};
if($@ || ref($env) ne 'HASH'){print STDERR "devwho: invalid child environment transport\n";exit 1}
remove_tree($directory);
%ENV=map { encode('utf8',$_)=>encode('utf8',$env->{$_}) } keys %$env;
{ no warnings 'exec'; exec {$ARGV[0]} @ARGV; }
my $code=$!{ENOENT}?127:($!{EACCES} || $!{ENOEXEC})?126:1;
print STDERR $code==127 ? "devwho: command not found\n" : $code==126 ? "devwho: command is not executable\n" : "devwho: cannot execute command\n";
exit $code;
