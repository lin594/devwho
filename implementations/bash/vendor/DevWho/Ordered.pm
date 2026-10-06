# Minimal insertion-ordered parser table. No DevWho policy lives in the parser.
package DevWho::Ordered;
use strict; use warnings;
sub new_hash { tie my %h, __PACKAGE__; return \%h }
sub TIEHASH { bless { keys=>[], values=>{}, index=>0 },shift }
sub STORE { my($s,$k,$v)=@_; push @{$s->{keys}},$k unless exists $s->{values}{$k}; $s->{values}{$k}=$v }
sub FETCH { $_[0]{values}{$_[1]} }
sub EXISTS { exists $_[0]{values}{$_[1]} }
sub FIRSTKEY { $_[0]{index}=0; $_[0]{keys}[0] }
sub NEXTKEY { $_[0]{keys}[++$_[0]{index}] }
sub SCALAR { scalar @{$_[0]{keys}} }
sub DELETE { my($s,$k)=@_; @{$s->{keys}}=grep {$_ ne $k} @{$s->{keys}}; delete $s->{values}{$k} }
sub CLEAR { $_[0]{keys}=[]; $_[0]{values}={} }
1;
