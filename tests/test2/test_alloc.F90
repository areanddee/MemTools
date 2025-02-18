 program test_alloc
 use iso_fortran_env, only: IK => int32, RK => real64
 use dims, only: n
 real(RK), allocatable :: a(:,:)
 allocate(a(1:n,1:n))
 a(:,:) = 1.0
 deallocate(a)

 end program test_alloc
