(define (problem delivery-x-2)
   (:domain mailrun)
   (:objects hamleta hamletb hamletc - hamlet
             scroll6 scroll5 scroll4 scroll3 scroll2 scroll1 - scroll
             courier1 courier2 - courier
             leftstrap1 rightstrap1 leftstrap2 rightstrap2 - satchel)
   (:init (= (mass scroll6) 1)
          (= (mass scroll5) 1)
          (= (mass scroll4) 1)
          (= (mass scroll3) 1)
          (= (mass scroll2) 1)
          (= (mass scroll1) 1)

          (resting scroll6 hamleta)
          (resting scroll5 hamleta)
          (resting scroll4 hamleta)
          (resting scroll3 hamleta)
          (resting scroll2 hamleta)
          (resting scroll1 hamleta)

          (posted-at courier1 hamleta)
          (posted-at courier2 hamleta)
          (idle leftstrap1)
          (idle rightstrap1)
          (idle leftstrap2)
          (idle rightstrap2)
          (attached leftstrap1 courier1)
          (attached rightstrap1 courier1)
          (attached leftstrap2 courier2)
          (attached rightstrap2 courier2)

          (road hamleta hamletb)
          (road hamletb hamleta)
          (road hamleta hamletc)
          (road hamletc hamleta)

          (= (current_pouch courier1) 0)
          (= (pouch_limit courier1) 4)
          (= (current_pouch courier2) 0)
          (= (pouch_limit courier2) 4)
          (= (toll) 0))


   (:goal (and (resting scroll6 hamletb)
               (resting scroll5 hamletb)
               (resting scroll4 hamletb)
               (resting scroll3 hamletb)
               (resting scroll2 hamletc)
               (resting scroll1 hamletc)))

   (:metric minimize (toll))
)
