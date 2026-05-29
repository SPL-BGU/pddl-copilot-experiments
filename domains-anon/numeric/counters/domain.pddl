(define (domain tankyard)
    (:requirements :strips :typing :equality :adl :fluents)
    (:types tank)
  (:predicates
    (idle ?x - tank)
  )

    (:functions
        (level ?c - tank);; - int  ;; The value shown in counter ?c
        (flowrate ?c - tank);;
        (capacity);; -  int ;; The maximum integer we consider - a static value
    )

    ;; Increment the value in the given counter by one
    (:action fill
         :parameters (?c - tank)
         :precondition (and (<= (+ (level ?c) (flowrate ?c)) (capacity)))
         :effect (and (increase (level ?c) (flowrate ?c)))
    )
    ;; Decrement the value in the given counter by one
    (:action drain
         :parameters (?c - tank)
         :precondition (and (>= (- (level ?c) (flowrate ?c)) 0))
         :effect (and (decrease (level ?c) (flowrate ?c)))
    )

    (:action open_valve
         :parameters (?c - tank)
         :precondition (and (<= (+ (flowrate ?c) 1) 10))
         :effect (and (increase (flowrate ?c) 1))
    )

    (:action close_valve
         :parameters (?c - tank)
         :precondition (and (>= (flowrate ?c) 1))
         :effect (and (decrease (flowrate ?c) 1))
    )
)
