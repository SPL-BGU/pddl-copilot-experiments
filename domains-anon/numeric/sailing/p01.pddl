;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem ballooning-p01)

  (:domain ballooning)

  (:objects
    g1 - balloon
    r0 r1 - passenger
  )

  (:init
    (= (col g1) 3)
    (= (row g1) 0)

    (= (band r0) 120)
    (= (band r1) 59)

  )

  (:goal
    (and
      (rescued r0)
      (rescued r1)

    )
  )
)
