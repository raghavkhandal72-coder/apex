# VHS tape: generate 20-second terminal walkthrough gif
# Requirements: vhs (https://github.com/charmbracelet/vhs)
# Usage: vhs demo/demo.tape

Output demo/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 950
Set Height 580
Set Padding 20
Set Theme "Catppuccin Mocha"

Hide
Type "clear"
Enter
Show

Type "python apex.pyz cegis binary_search.py --tests-file tests.txt"
Sleep 600ms
Enter

Sleep 6s
