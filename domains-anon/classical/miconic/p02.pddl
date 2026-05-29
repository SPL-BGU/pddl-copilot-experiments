


(define (problem submersible-p02)
   (:domain submersible)
   (:objects diver0 diver1 - diver
             deck0 deck1 - deck)


(:init
(shallower_than deck0 deck1)



(embarks_at diver0 deck1)
(disembarks_at diver0 deck0)

(embarks_at diver1 deck1)
(disembarks_at diver1 deck0)






(pod-at deck0)
)


(:goal (and
(delivered diver0)
(delivered diver1)
))
)
