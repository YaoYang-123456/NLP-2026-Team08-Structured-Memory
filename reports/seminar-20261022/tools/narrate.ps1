param([string]$ContentPath,[string]$OutDir)
Add-Type -AssemblyName System.Speech
$data=Get-Content -LiteralPath $ContentPath -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$tts=[System.Speech.Synthesis.SpeechSynthesizer]::new()
$tts.SelectVoice('Microsoft Huihui Desktop')
$tts.Rate=-1
$results=@()
try {
 for($i=0;$i -lt 9;$i++) {
  $path=Join-Path $OutDir ('page-{0:d2}.wav' -f ($i+1))
  if(Test-Path -LiteralPath $path){throw 'Refusing to replace audio'}
  $tts.SetOutputToWaveFile($path)
  $tts.Speak($data.slides[$i].speech)
  $tts.SetOutputToNull()
  $results+=@{page=$i+1;voice=$tts.Voice.Name;rate=$tts.Rate;file=$path;planned_seconds=$data.slides[$i].seconds;synthetic=$true}
 }
} finally {$tts.Dispose()}
$results | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $OutDir 'voice-settings.json') -Encoding utf8
