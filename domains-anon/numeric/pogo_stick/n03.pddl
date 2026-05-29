(define (problem ceramicsstudio-n03)
  (:domain ceramicsstudio)
  (:objects
    tile0 tile1 tile2 tile3 tile4 tile5 tile6 tile7 tile8 tile9 tile10 tile11 tile12 tile13 tile14 tile15 tile16 tile17 tile18 tile19 tile20 tile21 tile23 tile24 tile25 tile26 tile27 tile28 tile29 tile30 tile31 tile32 tile33 tile34 tile35 - tile
  )
  (:init (standing_on tile7) (empty_tile tile0) (empty_tile tile1) (empty_tile tile2) (empty_tile tile3) (empty_tile tile4) (empty_tile tile5) (empty_tile tile6) (empty_tile tile7) (empty_tile tile9) (empty_tile tile10) (empty_tile tile11) (empty_tile tile12) (empty_tile tile13) (empty_tile tile14) (empty_tile tile16) (empty_tile tile17) (empty_tile tile18) (empty_tile tile20) (empty_tile tile21) (empty_tile tile23) (empty_tile tile24) (empty_tile tile25) (empty_tile tile26) (empty_tile tile27) (empty_tile tile28) (empty_tile tile29) (empty_tile tile30) (empty_tile tile31) (empty_tile tile32) (empty_tile tile33) (empty_tile tile34) (empty_tile tile35) (clay_tile tile19) (clay_tile tile8) (clay_tile tile15)
    (kiln_tile kiln_block) (= (count_raw_clay_on_shelf) 0) (= (count_wedged_clay_on_shelf) 2) (= (count_coils_on_shelf) 7) (= (count_glaze_jar_on_shelf) 0) (= (count_bisque_mold_on_shelf) 0)
  )
  (:goal
    (and
      (undef_pred_xyz)
    )
  )
)
