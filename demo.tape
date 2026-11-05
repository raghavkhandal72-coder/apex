# VHS tape for Apex Show HN terminal demo
# Run: vhs demo.tape -> generates apex_demo.gif

Output apex_demo.gif

Set FontSize 15
Set Width 1100
Set Height 650
Set Theme "Catppuccin Mocha"
Set Padding 20
Set PlaybackSpeed 1.2

Type "python dist/apex.pyz 'Build thread-safe LRU Cache' --offline"
Sleep 400ms
Enter
Sleep 4s

Type "python dist/apex.pyz cegis examples/calculator.py --tests 'assert add(2, 3) == 5'"
Sleep 400ms
Enter
Sleep 4s

Type "python dist/apex.pyz sbfl examples/calculator.py --tests 'assert add(2, 3) == 5'"
Sleep 400ms
Enter
Sleep 3s
