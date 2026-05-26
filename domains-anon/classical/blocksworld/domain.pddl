(define (domain tearoom)
  (:requirements :strips :typing)
  (:types bowl)
  (:predicates (set_on ?x - bowl ?y - bowl)
         (on_tatami ?x - bowl)
         (unstacked ?x - bowl)
         (hands_idle)
         (cradling ?x - bowl)
         )

  (:action lift_bowl
       :parameters (?x - bowl)
       :precondition (and (unstacked ?x) (on_tatami ?x) (hands_idle))
       :effect
       (and (not (on_tatami ?x))
       (not (unstacked ?x))
       (not (hands_idle))
       (cradling ?x)))

  (:action place_bowl
       :parameters (?x - bowl)
       :precondition (cradling ?x)
       :effect
       (and (not (cradling ?x))
       (unstacked ?x)
       (hands_idle)
       (on_tatami ?x)))

  (:action nest_atop
       :parameters (?x - bowl ?y - bowl)
       :precondition (and (cradling ?x) (unstacked ?y))
       :effect
       (and (not (cradling ?x))
       (not (unstacked ?y))
       (unstacked ?x)
       (hands_idle)
       (set_on ?x ?y)))
  (:action separate_atop
       :parameters (?x - bowl ?y - bowl)
       :precondition (and (set_on ?x ?y) (unstacked ?x) (hands_idle))
       :effect
       (and (cradling ?x)
       (unstacked ?y)
       (not (unstacked ?x))
       (not (hands_idle))
       (not (set_on ?x ?y))))

)
