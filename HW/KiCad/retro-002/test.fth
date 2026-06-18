
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

