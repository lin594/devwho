#!/usr/bin/env perl
# JSON transport decoder: reject trailing documents and non-integer numbers.
# The v1 transport has only one numeric field (integer version); no policy here.
use strict; use warnings; use JSON::PP;
local $/;
my $out=eval { my $value=JSON::PP->new->utf8->allow_bignum->decode(<>); JSON::PP->new->utf8->encode($value) };
if($@){ print STDERR "devwho: Invalid DevWho shell state\n";exit 1 }
print $out;
