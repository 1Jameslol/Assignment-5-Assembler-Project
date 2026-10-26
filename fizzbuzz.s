# Example MIPS FizzBuzz source for the assignment.
.data
msg_fizz: .asciiz "Fizz\n"
msg_buzz: .asciiz "Buzz\n"
msg_fizzbuzz: .asciiz "FizzBuzz\n"
.text
main:
    addi $t0, $zero, 1
    addi $t1, $zero, 16
loop:
    beq $t0, $t1, done
    addi $t0, $t0, 1
    j loop
done:
    addi $v0, $zero, 10
    syscall
