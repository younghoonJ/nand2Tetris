// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

// Put your code here.

@8192 // 256 * 32
D=A
@SCREEN
D=D+A
@rmax
M=D

(SET)
    @SCREEN // screen init position
    D=A
    @pos
    M=D
    @KBD // set color
    D=M
    @BLACK
    D;JNE
(WHITE)
    @pos
    D=M
    @rmax
    D=D-M
    @SET
    D;JEQ
    @pos
    A=M
    M=0
    @pos
    M=M+1
    @WHITE
    0;JEQ
(BLACK)
    @pos
    D=M
    @rmax
    D=D-M
    @SET
    D;JEQ
    @pos
    A=M
    M=-1
    @pos
    M=M+1
    @BLACK
    0;JEQ
