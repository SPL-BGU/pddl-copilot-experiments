(define (domain submersible)
(:requirements :typing)
(:types deck diver)

(:predicates
    (embarks_at ?person - diver ?floor - deck)
    (disembarks_at ?person - diver ?floor - deck)
    (shallower_than ?floor1 - deck ?floor2 - deck)
    (submerged ?person - diver)
    (delivered ?person - diver)
    (pod-at ?floor - deck))

(:action pressurize
    :parameters (?f - deck ?p - diver)
    :precondition (and (pod-at ?f) (embarks_at ?p ?f))
    :effect (submerged ?p))

(:action egress
    :parameters (?f - deck ?p - diver)
    :precondition (and (pod-at ?f) (disembarks_at ?p ?f) (submerged ?p))
    :effect (and (not (submerged ?p))          (delivered ?p))) ;;drive up

(:action ascend
    :parameters (?f1 - deck ?f2 - deck)
    :precondition (and (pod-at ?f1) (shallower_than ?f1 ?f2))
    :effect (and (pod-at ?f2) (not (pod-at ?f1))))   ;;drive down

(:action descend
    :parameters (?f1 - deck ?f2 - deck)
    :precondition (and (pod-at ?f1) (shallower_than ?f2 ?f1))
    :effect (and (pod-at ?f2) (not (pod-at ?f1))))

)
)
