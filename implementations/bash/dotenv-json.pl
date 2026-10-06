#!/usr/bin/env perl
# Strict optional dotenv frontend. Parsing only; schema/transition rules stay in jq.
use strict;use warnings;use JSON::PP;use Encode qw(decode FB_CROAK);
local $/;
my $out=eval {
 open my $fh,'<:raw',$ARGV[0] or die 'read';my $raw=<$fh>;
 my $source=decode('utf8',$raw,FB_CROAK);
 die 'unicode' if $source =~ /[\x{D800}-\x{DFFF}]|[^\x{0}-\x{10FFFF}]/;
 $source =~ s/\r\n/\n/g;die 'control' if $source =~ /[\r\0]/;
 my %env;
 for my $line (split /\n/,$source,-1) {
  next if $line =~ /\A[ \t]*(?:#.*)?\z/;
  $line =~ s/\A[ \t]*//;
  $line =~ s/\Aexport //;
  $line =~ /\A([A-Za-z_][A-Za-z0-9_]*)[ \t]*=(.*)\z/ or die 'assignment';
  my($key,$raw)=($1,$2);die 'duplicate' if exists $env{$key};
  my $value;
  if($raw =~ /\A[ \t]*'/) {
   $raw =~ /\A[ \t]*'([^']*)'[ \t]*(?:#.*)?\z/ or die 'quote';$value=$1;
  } elsif($raw =~ /\A[ \t]*"/) {
   $raw =~ /\A[ \t]*("(?:[^"\\]|\\.)*")[ \t]*(?:#.*)?\z/ or die 'quote';
   $value=JSON::PP->new->decode($1);
   die 'unicode' if $value =~ /[\x{D800}-\x{DFFF}]/;
  } else {
   $raw =~ s/[ \t]+#.*\z//;$raw =~ s/\A[ \t]+//;$raw =~ s/[ \t]+\z//;$value=$raw;
  }
  die 'nul' if $value =~ /\0/;$env{$key}=$value;
 }
 my $selected=$ARGV[1];
 if(exists $env{DEVWHO_PROFILE}) {
  die 'mismatch' if length($selected) && $selected ne $env{DEVWHO_PROFILE};
  $selected=delete $env{DEVWHO_PROFILE};
 }
 die 'profile' unless $selected =~ /\A[A-Za-z0-9][A-Za-z0-9_.-]*\z/;
 JSON::PP->new->utf8->encode({version=>1,settings=>{shortcut_profile=>$selected},profiles=>{$selected=>{env=>\%env}}});
};
if($@){print STDERR "devwho: Invalid dotenv file or profile selection\n";exit 1}print $out;
