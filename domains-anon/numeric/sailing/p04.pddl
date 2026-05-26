;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem ballooning-p04)

	(:domain ballooning)

	(:objects
		g0 - balloon
		r0 r1 - passenger
	)

  (:init
		(= (col g0) 1)
(= (row g0) 0)

		(= (band r0) 0)
(= (band r1) 2)

	)

	(:goal
		(and
			(rescued r0)
(rescued r1)
		)
	)
)

