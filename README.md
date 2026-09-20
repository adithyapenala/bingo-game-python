# Bingo-game
A two player mini game, using python flask and javascript

# How to play
## step 1
Populate 5x5 matrix with numbers 1 to 25 in random order.

## step 2
The player selects a number from 1 to 25, which is not struck off, and notifies the other player of his choice.

## step 3
After every turn player checks for:

All elements in a row struck off.
All elements in a column struck off.
All elements in a diagonal struck off.
If true then a point is added.

## Win condition
First player to score more than or equal to 5 points.
