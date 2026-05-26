(define (domain seaport)
(:requirements :strips :typing)
(:types harbour harbour_asset - object
  dock wharf - harbour
        barge derrick deck - harbour_asset
        pontoon bale - deck)

(:predicates (moored_at ?x - harbour_asset ?y - harbour)
             (stowed_on ?x - bale ?y - deck)
             (loaded_in ?x - bale ?y - barge)
             (hoisting ?x - derrick ?y - bale)
             (ready ?x - derrick)
             (empty ?x - deck))

(:action sail
  :parameters (?x - barge ?y - harbour ?z - harbour)
  :precondition (and (moored_at ?x ?y))
  :effect (and (not (moored_at ?x ?y)) (moored_at ?x ?z)))

(:action hoist_up
  :parameters (?x - derrick ?y - bale ?z - deck ?p - harbour)
  :precondition (and (moored_at ?x ?p) (ready ?x) (moored_at ?y ?p) (stowed_on ?y ?z) (empty ?y))
  :effect (and (not (moored_at ?y ?p)) (hoisting ?x ?y) (not (empty ?y)) (not (ready ?x)) (empty ?z) (not (stowed_on ?y ?z))))

(:action lower_down
  :parameters (?x - derrick ?y - bale ?z - deck ?p - harbour)
  :precondition (and (moored_at ?x ?p) (moored_at ?z ?p) (empty ?z) (hoisting ?x ?y))
  :effect (and (ready ?x) (not (hoisting ?x ?y)) (moored_at ?y ?p) (not (empty ?z)) (empty ?y)(stowed_on ?y ?z)))

(:action stow
  :parameters (?x - derrick ?y - bale ?z - barge ?p - harbour)
  :precondition (and (moored_at ?x ?p) (moored_at ?z ?p) (hoisting ?x ?y))
  :effect (and (not (hoisting ?x ?y)) (loaded_in ?y ?z) (ready ?x)))

(:action unstow
  :parameters (?x - derrick ?y - bale ?z - barge ?p - harbour)
  :precondition (and (moored_at ?x ?p) (moored_at ?z ?p) (ready ?x) (loaded_in ?y ?z))
  :effect (and (not (loaded_in ?y ?z)) (not (ready ?x)) (hoisting ?x ?y)))

)
