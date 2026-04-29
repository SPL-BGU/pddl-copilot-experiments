;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem instance_1_2)

	(:domain sailing)

	(:objects
		b0 - boat
		p0 p1 - person
	)

  (:init
		(= (x b0) -2)
(= (y b0) 0)

		(= (d p0) 1)
(= (d p1) 2)

	)

	(:goal
		(and
			(saved p0)
(saved p1)
		)
	)
)

