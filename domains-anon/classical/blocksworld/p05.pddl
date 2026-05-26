

(define (problem tearoom-p05)
(:domain tearoom)
(:objects bowl1 bowl2 bowl3 bowl4 bowl5 bowl6  - bowl)
(:init
(hands_idle)
(on_tatami bowl1)
(on_tatami bowl2)
(set_on bowl3 bowl5)
(set_on bowl4 bowl1)
(set_on bowl5 bowl6)
(on_tatami bowl6)
(unstacked bowl2)
(unstacked bowl3)
(unstacked bowl4)
)
(:goal
(and
(set_on bowl1 bowl2)
(set_on bowl2 bowl6)
(set_on bowl3 bowl4))
)
)


