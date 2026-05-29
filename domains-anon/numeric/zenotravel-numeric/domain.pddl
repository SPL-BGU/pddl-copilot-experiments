;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (domain lunar-logistics)
;(:requirements :typing :fluents)
(:types surface_unit outpost - object
  rover crew - surface_unit)
(:predicates (stationed ?x - surface_unit  ?c - outpost)
             (aboard ?p - crew ?a - rover))
(:functions (regolith ?a - rover)
            (gap ?c1 - outpost ?c2 - outpost)
            (idle-draw ?a - rover)
            (rush-draw ?a - rover)
            (hopper ?a - rover)
            (total-regolith-spent)
      (occupants ?a - rover)
            (rush-cap ?a - rover)
            )


(:action embark_crew
 :parameters (?p - crew ?a - rover ?c - outpost)
 :precondition (and (stationed ?p ?c)
                 (stationed ?a ?c))
 :effect (and (not (stationed ?p ?c))
              (aboard ?p ?a)
    (increase (occupants ?a) 1)))


(:action disembark_crew
 :parameters (?p - crew ?a - rover ?c - outpost)
 :precondition (and (aboard ?p ?a)
                 (stationed ?a ?c))
 :effect (and (not (aboard ?p ?a))
              (stationed ?p ?c)
    (decrease (occupants ?a) 1)))

(:action traverse-idle
 :parameters (?a - rover ?c1 ?c2 - outpost)
 :precondition (and (stationed ?a ?c1)
                 (>= (regolith ?a)
                         (* (gap ?c1 ?c2) (idle-draw ?a))))
 :effect (and (not (stationed ?a ?c1))
              (stationed ?a ?c2)
              (increase (total-regolith-spent)
                         (* (gap ?c1 ?c2) (idle-draw ?a)))
              (decrease (regolith ?a)
                         (* (gap ?c1 ?c2) (idle-draw ?a)))))

(:action traverse-rush
 :parameters (?a - rover ?c1 ?c2 - outpost)
 :precondition (and (stationed ?a ?c1)
                 (>= (regolith ?a)
                         (* (gap ?c1 ?c2) (rush-draw ?a)))
                 (<= (occupants ?a) (rush-cap ?a)))
 :effect (and (not (stationed ?a ?c1))
              (stationed ?a ?c2)
              (increase (total-regolith-spent)
                         (* (gap ?c1 ?c2) (rush-draw ?a)))
              (decrease (regolith ?a)
                         (* (gap ?c1 ?c2) (rush-draw ?a)))
  )
)

(:action refill_regolith
 :parameters (?a - rover)
 :precondition (and (> (hopper ?a) (regolith ?a))

    )
 :effect (and (assign (regolith ?a) (hopper ?a)))
)


)
