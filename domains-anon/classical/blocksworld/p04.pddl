

(define (problem tearoom-p04)
(:domain tearoom)
(:objects bowl1 bowl2 bowl3 bowl4 bowl5  - bowl)
(:init
(hands_idle)
(on_tatami bowl1)
(on_tatami bowl2)
(set_on bowl3 bowl2)
(set_on bowl4 bowl5)
(on_tatami bowl5)
(unstacked bowl1)
(unstacked bowl3)
(unstacked bowl4)
)
(:goal
(and
(set_on bowl2 bowl5)
(set_on bowl3 bowl2)
(set_on bowl4 bowl1))
)
)


