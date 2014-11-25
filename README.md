MacTips
=======

Setup of MacPro (OS X 10.10, Yosemite) for Computing in Earth System Science 
----------------------------------------------------------------------------

Science libraries for Mac can be installed quite easily via the MacPorts project from http://www.macports.org
(To install it go to http://www.macports.org/install.php ) and use then the "port install" command line. 
The software available is listed on the macports website and below a selection of ports installation. 
The Yosemite Java Runtime Environment provided by Apple is needed http://support.apple.com/kb/DL1572 . 
Here a list of "port install" commands that installed (under /opt/local) rather safely for me:

sudo port install wget

sudo port install llvm3.5 (see problem solving at: https://trac.macports.org/ticket/45517)

sudo port install gcc48

sudo port install grib_api

sudo port install hdf5

sudo port install netcdf

sudo port install netcdf-fortran

sudo port install ncview

sudo port install nco +netcdf

sudo port install cdo       

sudo port install octave

sudo port install xmgr

sudo port install geos

sudo port install ImageMagick

sudo port install xv

sudo port install gv

---

Fortran:
--------
The fortran compiler can be also obtained from http://hpc.sourceforge.net . 

In case of MLion/Yosemite gcc4.8/gcc5.0 can be chosen as have gfortran (with OpenMP):

wget http://prdownloads.sourceforge.net/hpc/gcc-5.0-bin.tar.gz

sudo tar -xvfz gcc-5.0-bin.tar.gz -C /. 

This will install it under /usr/local

The compilation of fortran code need few adjustments in the config file:

CDFLIB =  -L/opt/local/lib -lnetcdff -fopenmp

CFLAGS = -m64 -arch x86_64 ...

FFLAGS = -c -m64 -arch x86_64 ...


OpenMPI:
--------
While OpenMP is standard and part of gcc/gfortran package, the MPI need to be installed and can be done via the port:

sudo port install mpich

OpenMPI is also free and a available here:

wget http://www.open-mpi.org/software/ompi/v1.6/downloads/openmpi-1.6.3.tar.gz

tar zxvf openmpi-1.6.3.tar.gz

./configure --prefix=/usr/local

make all

sudo make install


Test files with OpenMP and OpenMPI are compiled as follows:

mpif90 mpihello.F90  ;  mpif90 -fopenmp mpiomp_hello.F90 


Scientific and numerical libraries in python:
---------------------------------------------
Python provides a collection of scientific and numerical software libraries that are easily installed via the ports:

sudo port install py-scipy

sudo port install py-numpy


Netcdf in python:
-----------------
for NetCDF4 the port is working fine

sudo port install py-netcdf4


Grib in python:
---------------
for Grib the port is working fine

sudo port install py-pygrib


Plotting with python:
---------------------
Python has also plotting software libraries, free and quite comprehensive, with a growing community also in NWP.
To plot on geography you can use the "basemap" lib (check its developer site here: http://matplotlib.org ).
This for me was installed (after having installed geos with port command and NetCDF/HDF5), more traditionnally as:

sudo port install py-matplotlib-basemap


Latex:
------
TexShop is a recommended front-end. For the actual LaTex library the "TexLive" distribution is recommended and can be installed via macports (since there are a lot of dependecies) as

sudo port install texlive

sudo ln -s /opt/local/bin /usr/texbin


This second command is needed to link the expected bin location to the macports installation location.
(if problems occur some instructions are available at: http://www.macfreek.nl/memory/LaTeX_installation_on_Mac )


Doxygen:
--------
To surf large codes such as NWP models a code tree library such as "doxygen" is recommended. 
Install with the port command:

sudo port install doxygen

sudo port install graphviz


Others:
-------
There are several Mac Users out there and a lot in NWP&Climate, that took the challenge of documenting installation procedures 
(eg. http://www.atmos.washington.edu/~salathe/osx_unix/ , so Google is a good companion to search for it!

------
Hope this is useful! Please feel free to post here any correction.
