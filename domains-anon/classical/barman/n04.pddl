(define (problem astrolabe-n04)
 (:domain astrolabe)
 (:objects
      prism1 - prism
      east_mount west_mount - mount
      lens1 lens2 - lens
      wavelength1 wavelength2 wavelength3 - wavelength
      spectrum1 spectrum2 - spectrum
      beacon1 beacon2 beacon3 - beacon
      magnitude0 magnitude1 magnitude2 - magnitude
)
 (:init
  (mounted prism1)
  (mounted lens1)
  (mounted lens2)
  (beams beacon1 wavelength1)
  (beams beacon2 wavelength2)
  (beams beacon3 wavelength3)
  (calibrated prism1)
  (calibrated lens1)
  (calibrated lens2)
  (vacant prism1)
  (vacant lens1)
  (vacant lens2)
  (mount_free east_mount)
  (mount_free west_mount)
  (prism_empty_magnitude prism1 magnitude0)
  (prism_magnitude prism1 magnitude0)
  (precedes magnitude0 magnitude1)
  (precedes magnitude1 magnitude2)
  (spectrum_band1 spectrum1 wavelength1)
  (spectrum_band2 spectrum1 wavelength2)
  (spectrum_band1 spectrum2 wavelength1)
  (spectrum_band2 spectrum2 wavelength3)
)
 (:goal
  (and
      (carries lens1 spectrum1)
      (carries lens2 spectrum2)
))))
