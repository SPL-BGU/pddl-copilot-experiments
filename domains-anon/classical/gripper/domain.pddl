(define (domain mailfloor)
 (:requirements :strips :typing)
 (:types bay parcel carrier hand)
 (:predicates (stationed-at ?r - carrier ?x - bay)
         (posted ?o - parcel ?x - bay)
        (vacant ?r - carrier ?g - hand)
        (bearing ?r - carrier ?o - parcel ?g - hand))

   (:action walk
       :parameters  (?r - carrier ?from ?to - bay)
       :precondition (and  (stationed-at ?r ?from))
       :effect (and  (stationed-at ?r ?to)
         (not (stationed-at ?r ?from))))

   (:action collect
       :parameters (?r - carrier ?obj - parcel ?room - bay ?g - hand)
       :precondition  (and  (posted ?obj ?room) (stationed-at ?r ?room) (vacant ?r ?g))
       :effect (and (bearing ?r ?obj ?g)
        (not (posted ?obj ?room))
        (not (vacant ?r ?g))))

   (:action deposit
       :parameters (?r - carrier ?obj - parcel ?room - bay ?g - hand)
       :precondition  (and  (bearing ?r ?obj ?g) (stationed-at ?r ?room))
       :effect (and (posted ?obj ?room)
        (vacant ?r ?g)
        (not (bearing ?r ?obj ?g)))))
