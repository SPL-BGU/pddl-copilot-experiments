(define (domain bush-expedition)
(:requirements :typing)
(:types jeep tourist - safari_entity
safari_entity waterhole range - object)
(:predicates (resting-at ?x - safari_entity ?c - waterhole)
             (riding-in ?p - tourist ?a - jeep)
       (tank-level ?a - jeep ?l - range)
       (follows ?l1 ?l2 - range))


(:action mount
 :parameters (?p - tourist ?a - jeep ?c - waterhole)

 :precondition (and (resting-at ?p ?c)
                 (resting-at ?a ?c))
 :effect (and (not (resting-at ?p ?c))
              (riding-in ?p ?a)))

(:action dismount
 :parameters (?p - tourist ?a - jeep ?c - waterhole)

 :precondition (and (riding-in ?p ?a)
                 (resting-at ?a ?c))
 :effect (and (not (riding-in ?p ?a))
              (resting-at ?p ?c)))

(:action cruise
 :parameters (?a - jeep ?c1 ?c2 - waterhole ?l1 ?l2 - range)

 :precondition (and (resting-at ?a ?c1)
                 (tank-level ?a ?l1)
     (follows ?l2 ?l1))
 :effect (and (not (resting-at ?a ?c1))
              (resting-at ?a ?c2)
              (not (tank-level ?a ?l1))
              (tank-level ?a ?l2)))

(:action dash
 :parameters (?a - jeep ?c1 ?c2 - waterhole ?l1 ?l2 ?l3 - range)

 :precondition (and (resting-at ?a ?c1)
                 (tank-level ?a ?l1)
     (follows ?l2 ?l1)
     (follows ?l3 ?l2)
    )
 :effect (and (not (resting-at ?a ?c1))
              (resting-at ?a ?c2)
              (not (tank-level ?a ?l1))
              (tank-level ?a ?l3)
  )
)

(:action replenish
 :parameters (?a - jeep ?c - waterhole ?l - range ?l1 - range)

 :precondition (and (tank-level ?a ?l)
                 (follows ?l ?l1)
                 (resting-at ?a ?c))
 :effect (and (tank-level ?a ?l1) (not (tank-level ?a ?l))))


)
