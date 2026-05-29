;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem tankyard-p03)
	(:domain tankyard)
	(:objects
		tank0 tank1 tank2 - tank
	)
  (:init
		(= (level tank0) 64)
	(= (level tank1) 19)
	(= (level tank2) 77)

        (= (flowrate tank0) 0)
	(= (flowrate tank1) 0)
	(= (flowrate tank2) 0)

		(= (capacity) 100)
	)
	(:goal
		(and
			(<= (+ (level tank0) 1) (level tank1))
	(<= (+ (level tank1) 1) (level tank2))
		)
	)
)

