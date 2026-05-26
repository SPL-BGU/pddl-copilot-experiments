(define (domain arable-farm)
(:requirements :strips :typing)
(:types tractor field hopper gauge variety silo plot)

(:predicates (ploughing ?x - tractor ?y - field)
             (anchored_at ?x - silo ?y - field)
             (can_furrow ?r - tractor ?x - field ?y - field)
       (fitted_for_seed_sampling ?r - tractor)
             (fitted_for_root_sampling ?r - tractor)
             (fitted_for_gauging ?r - tractor)
             (unfilled ?s - hopper)
             (have_root_sample ?r - tractor ?w - field)
             (have_seed_sample ?r - tractor ?w - field)
             (filled ?s - hopper)
       (tuned ?c - gauge ?r - tractor)
       (handles ?c - gauge ?m - variety)
             (ready ?r - tractor)
             (reachable ?w - field ?p - field)
             (have_reading ?r - tractor ?o - plot ?m - variety)
             (reported_seed_data ?w - field)
             (reported_root_data ?w - field)
             (reported_reading_data ?o - plot ?m - variety)
       (has_seed_clump ?w - field)
       (has_root_clump ?w - field)
             (reachable_from ?o - plot ?w - field)
       (hopper_of ?s - hopper ?r - tractor)
       (tuning_plot ?i - gauge ?o - plot)
       (mounted_on ?i - gauge ?r - tractor)
       (relay_open ?l - silo))

(:action furrow_to
:parameters (?x - tractor ?y - field ?z - field)
:precondition (and (can_furrow ?x ?y ?z) (ready ?x) (ploughing ?x ?y)
                (reachable ?y ?z))
:effect (and (not (ploughing ?x ?y)) (ploughing ?x ?z) (visited ?x ?z)))

(:action gather_seed
:parameters (?x - tractor ?s - hopper ?p - field)
:precondition (and (ploughing ?x ?p) (has_seed_clump ?p)
       (fitted_for_seed_sampling ?x) (hopper_of ?s ?x) (unfilled ?s))
:effect (and (not (unfilled ?s)) (filled ?s) (have_seed_sample ?x ?p)
       (not (has_seed_clump ?p))))

(:action gather_root
:parameters (?x - tractor ?s - hopper ?p - field)
:precondition (and (ploughing ?x ?p) (has_root_clump ?p)
             (fitted_for_root_sampling ?x) (hopper_of ?s ?x)(unfilled ?s))
:effect (and (not (unfilled ?s)) (filled ?s) (have_root_sample ?x ?p)
       (not (has_root_clump ?p))))

(:action empty_out
:parameters (?x - tractor ?y - hopper)
:precondition (and (hopper_of ?y ?x) (filled ?y))
:effect (and (not (filled ?y)) (unfilled ?y)))



(:action tune
 :parameters (?r - tractor ?i - gauge ?t - plot ?w - field)
 :precondition (and (fitted_for_gauging ?r) (tuning_plot ?i ?t)
              (ploughing ?r ?w) (reachable_from ?t ?w)(mounted_on ?i ?r))
 :effect (tuned ?i ?r))

(:action take_reading
 :parameters (?r - tractor ?p - field ?o - plot ?i - gauge ?m - variety)
 :precondition (and (tuned ?i ?r) (mounted_on ?i ?r) (fitted_for_gauging ?r)
                      (handles ?i ?m) (reachable_from ?o ?p) (ploughing ?r ?p))
 :effect (and (have_reading ?r ?o ?m)(not (tuned ?i ?r))))

(:action report_seed_data
 :parameters (?r - tractor ?l - silo ?p - field ?x - field ?y - field)
 :precondition (and (ploughing ?r ?x)(anchored_at ?l ?y)(have_seed_sample ?r ?p)
                   (reachable ?x ?y)(ready ?r)(relay_open ?l))
 :effect (and (not (ready ?r))(not (relay_open ?l))(relay_open ?l)
    (reported_seed_data ?p)(ready ?r)))

(:action report_root_data
 :parameters (?r - tractor ?l - silo ?p - field ?x - field ?y - field)
 :precondition (and (ploughing ?r ?x)(anchored_at ?l ?y)(have_root_sample ?r ?p)
                   (reachable ?x ?y)(ready ?r)(relay_open ?l))
 :effect (and (not (ready ?r))(not (relay_open ?l))
        (relay_open ?l)(reported_root_data ?p)(ready ?r)))


(:action report_reading_data
 :parameters (?r - tractor ?l - silo ?o - plot ?m - variety ?x - field ?y - field)
 :precondition (and (ploughing ?r ?x)(anchored_at ?l ?y)(have_reading ?r ?o ?m)
              (reachable ?x ?y)(ready ?r)(relay_open ?l))
 :effect (and (not (ready ?r))(not (relay_open ?l))(relay_open ?l)
        (reported_reading_data ?o ?m)(ready ?r)))
)
