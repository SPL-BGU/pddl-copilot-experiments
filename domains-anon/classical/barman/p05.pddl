(define (problem astrolabe-p05)
 (:domain astrolabe)
 (:objects 
     prism1 - prism
     east_mount west_mount - mount
     lens1 lens2 lens3 lens4 lens5 - lens
     wavelength1 wavelength2 wavelength3 - wavelength
     spectrum1 spectrum2 spectrum3 - spectrum
     beacon1 beacon2 beacon3 - beacon
     magnitude0 magnitude1 magnitude2 - magnitude
)
 (:init 
  (mounted prism1)
  (mounted lens1)
  (mounted lens2)
  (mounted lens3)
  (mounted lens4)
  (mounted lens5)
  (beams beacon1 wavelength1)
  (beams beacon2 wavelength2)
  (beams beacon3 wavelength3)
  (calibrated prism1)
  (calibrated lens1)
  (calibrated lens2)
  (calibrated lens3)
  (calibrated lens4)
  (calibrated lens5)
  (vacant prism1)
  (vacant lens1)
  (vacant lens2)
  (vacant lens3)
  (vacant lens4)
  (vacant lens5)
  (mount_free east_mount)
  (mount_free west_mount)
  (prism_empty_magnitude prism1 magnitude0)
  (prism_magnitude prism1 magnitude0)
  (precedes magnitude0 magnitude1)
  (precedes magnitude1 magnitude2)
  (spectrum_band1 spectrum1 wavelength2)
  (spectrum_band2 spectrum1 wavelength1)
  (spectrum_band1 spectrum2 wavelength2)
  (spectrum_band2 spectrum2 wavelength1)
  (spectrum_band1 spectrum3 wavelength2)
  (spectrum_band2 spectrum3 wavelength3)
)
 (:goal
  (and
     (carries lens1 spectrum2)
     (carries lens2 spectrum1)
     (carries lens3 spectrum3)
     (carries lens4 wavelength1)
)))
