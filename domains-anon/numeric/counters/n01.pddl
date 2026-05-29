;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem tankyard-n01)
  (:domain tankyard)
  (:objects
    tank0 tank1 tank2 tank3 tank4 - tank
  )
  (:init
    (= (level tank0) 12)
  (= (level tank1) 49)
  (= (level tank2) 93)
  (= (level tank3) 23)
  (= (level tank4) 79)

        (= (flowrate tank0) 0)
  (= (flowrate tank1) 0)
  (= (flowrate tank2) 0)
  (= (flowrate tank3) 0)
  (= (flowrate tank4) 0)

    (= (capacity) 100)
  )
)
