
hex
: CRLF a EMIT D EMIT ;
: binnum ( x -- ) ( print as 0000 )
	DUP 8 AND IF 1 ELSE 0 THEN . 
	DUP 4 AND IF 1 ELSE 0 THEN . 
	DUP 2 AND IF 1 ELSE 0 THEN . 
	DUP 1 AND IF 1 ELSE 0 THEN . 
	DROP
	;
: SP 20 EMIT ;
: 2bin ( x -- ) ( print as 0000.0000.0000.0000 )
	DUP 1000 / binnum SP
	DUP 100 / binnum SP
	DUP 10 / binnum SP
	DUP 1 / binnum SP
	DROP
	;
: x ( addr -- ) ( send addr to ports F K (A0..15) and print it)
	BASE C@ SWAP
	CRLF ." Addr: " DUP hex . ." ; bin: " DUP 2bin ." ; "
	ff DDRF C! ff DDRK C!
	DUP  100 / PORTK C! ff AND PORTF C!
	BASE C!
	;

: y 
	7000 x KEY DROP 
	8000 x KEY DROP
	9000 x KEY DROP
	A000 BEGIN
		DUP x KEY DROP 1+ 
		DUP A022 = UNTIL
	DROP 
	A040 x KEY DROP
	A060 x KEY DROP
	A100 x KEY DROP
	;
