

(define (problem BW-rand-4)
(:domain tearoom)
(:objects bowl1 bowl2 bowl3 bowl4  - bowl)
(:init
(hands_idle)
(set_on bowl1 bowl3)
(on_tatami bowl2)
(on_tatami bowl3)
(set_on bowl4 bowl2)
(unstacked bowl1)
(unstacked bowl4)
)
(:goal
(and
(set_on bowl2 bowl4)
(set_on bowl3 bowl2))
)
)


