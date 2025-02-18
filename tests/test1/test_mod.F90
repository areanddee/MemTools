module test_mod
  use iso_c_binding, only: c_double, c_float
  implicit none
  private

#ifdef SPMD
  real(c_double), dimension(nx,ny) :: field1  ! Should be included with SPMD defined
  real(c_float), dimension(nx,ny) :: field2   ! Testing float type
#endif

#ifdef UNDEFINED_FLAG
  real(c_double), dimension(100,100) :: field3  ! Should be excluded
#endif

#if defined(SPMD) && defined(DEBUG)
  real(c_double), allocatable :: field4(:,:)  ! Should be excluded if DEBUG undefined
#endif

end module test_mod
