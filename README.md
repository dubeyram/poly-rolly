# poly-rolly
A GUI dice roller in Python 3, tkinter

## Cryptographically strong pseudo-random number generation
Using Python's random.SystemRandom (which in turn uses os.random)

## Option to use random.org's HTTP API for true-random number generation
Toggable from the Edit menu, off by default

## Load/Save your configuration from/to a JSON file
From the File menu or with keyboard shortcuts

## Configure individual rollers by:
1. Number of dice
2. Number of faces
3. Modifier to each roll
4. Modifier to total roll

## Groups, and the ability to concurrently execute all rolls within a group
Just click the group-level roll button

## Move, rename and clone rollers or groups
Through the group/roller action menu

## Roll history (which is also saved to your JSON file)
Navigate by clicking the '<' and '>' group-level buttons

## Repeat last command
From the Edit menu, or with a keystroke
