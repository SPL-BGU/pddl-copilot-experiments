;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem instance_1_2)

	(:domain ballooning)

	(:objects
		g0 - balloon
		r0 r1 - passenger
	)

  (:init
		(= (col g0) -2)
(= (row g0) 0)

		(= (band r0) 1)
(= (band r1) 2)

	)

	(:goal
		(and
			(rescued r0)
(rescued r1)
		)
	)
)

