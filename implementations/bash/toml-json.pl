#!/usr/bin/env perl
# Parsing adapter only; configuration policy and transition rules are in core.jq.
use strict; use warnings;
use FindBin; use lib "$FindBin::Bin/vendor";
use JSON::PP; use TOML::Tiny::Parser;
local $/;
my $json=eval {
 local $SIG{__WARN__}=sub { die "Invalid TOML" };
 open my $fh,'<:raw',$ARGV[0] or die 'read'; my $source=<$fh>;
 my $parser=TOML::Tiny::Parser->new(strict=>1,
   inflate_boolean=>sub { $_[0] eq 'true' ? JSON::PP::true : JSON::PP::false },
   inflate_float=>sub { die 'floats are unsupported by this schema' },
   inflate_datetime=>sub { die 'dates are unsupported by this schema' });
 JSON::PP->new->utf8->encode($parser->parse($source));
};
if($@){ print STDERR "devwho: Invalid TOML configuration\n";exit 1 }
print $json;
