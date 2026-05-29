(define (domain joust-circuit)
(:requirements :strips :typing)
(:types arena competitor rank - object
  keep pavilion - arena
  knight trophy - competitor)

(:predicates (carried ?g - trophy ?t - knight ?l - rank)
       (for-claim ?g - trophy ?m - pavilion ?l - rank)
       (kept ?g - trophy ?l - rank)
       (offered ?g - trophy ?m -  pavilion ?l - rank)
       (succeeds ?l1 ?l2 - rank)
       (posted-at ?t - knight ?p - arena)
       (linked-to ?p1 ?p2 - arena))

(:action ride
 :parameters (?t - knight ?from ?to - arena)
 :precondition (and (posted-at ?t ?from) (linked-to ?from ?to))
 :effect (and (not (posted-at ?t ?from)) (posted-at ?t ?to)))

; ### LOAD ###
; ?l1 is the level of ?g ready to be loaded at ?m before loading
; ?l2 is the level of ?g ready to be loaded at ?m after loading
; ?l3 is the level of ?g in ?t before loading
; ?l4 is the level of ?g in ?t after loading

(:action claim
 :parameters (?g - trophy ?t - knight ?m - pavilion ?l1 ?l2 ?l3 ?l4 - rank)
 :precondition (and (posted-at ?t ?m) (carried ?g ?t ?l3)
        (for-claim ?g ?m ?l2) (succeeds ?l2 ?l1) (succeeds ?l4 ?l3))
 :effect (and (carried ?g ?t ?l4) (not (carried ?g ?t ?l3))
        (for-claim ?g ?m ?l1) (not (for-claim ?g ?m ?l2))))


; ### UNLOAD ###
; ?l1 is the level of ?g in ?t before unloading
; ?l2 is the level of ?g in ?t after unloading
; ?l3 is the level of ?g in ?d before unloading
; ?l4 is the level of ?g in ?d after unloading

(:action stash
 :parameters (?g - trophy ?t - knight ?d - keep ?l1 ?l2 ?l3 ?l4 - rank)
 :precondition (and (posted-at ?t ?d) (carried ?g ?t ?l2)
        (kept ?g ?l3) (succeeds ?l2 ?l1) (succeeds ?l4 ?l3))
 :effect (and (carried ?g ?t ?l1) (not (carried ?g ?t ?l2))
        (kept ?g ?l4) (not (kept ?g ?l3))))


; ### BUY ###
; ?l1 is the level of ?g on sale at ?m before buying
; ?l2 is the level of ?g on sale at ?m after buying
; ?l3 is the level of ?g ready to be loaded at ?m before buying
; ?l4 is the level of ?g ready to be loaded at ?m after buying

(:action seize
 :parameters (?t - knight ?g - trophy ?m - pavilion ?l1 ?l2 ?l3 ?l4 - rank)
 :precondition (and (posted-at ?t ?m) (offered ?g ?m ?l2) (for-claim ?g ?m ?l3)
        (succeeds ?l2 ?l1) (succeeds ?l4 ?l3))
 :effect (and (offered ?g ?m ?l1) (not (offered ?g ?m ?l2))
        (for-claim ?g ?m ?l4) (not (for-claim ?g ?m ?l3))))
))
