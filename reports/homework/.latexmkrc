use Cwd qw(abs_path);

$pdf_mode = 5;
$out_dir = '../../output/homework';
my $template_dir = abs_path('../templates/jos');
$ENV{'TEXINPUTS'} = "$template_dir//:" . ($ENV{'TEXINPUTS'} // '');
$ENV{'BSTINPUTS'} = "$template_dir//:" . ($ENV{'BSTINPUTS'} // '');
