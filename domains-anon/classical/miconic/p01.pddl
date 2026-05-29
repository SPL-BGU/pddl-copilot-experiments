


(define (problem submersible-p01)
   (:domain submersible)
   (:objects diver0 - diver
             deck0 deck1 - deck)


(:init
(shallower_than deck0 deck1)



(embarks_at diver0 deck0)
(disembarks_at diver0 deck1)






(pod-at deck0)
)


(:goal (and
(delivered diver0)
))
)
