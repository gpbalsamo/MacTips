MacTips
=======

Software and tips for Mac scientific users

Setup of MacPro (OS X 10.8.3) for scientific (NWP) computing
-------------------------------------------------------------
by Gianpaolo Balsamo (pad@ecmwf.int, January 2013).

Science libraries for Mac can be installed quite easily via MacPorts software from http://www.macports.org
(To install it go to http://www.macports.org/install.php ) and using the "port install" command line. 
The software available is listed on the macports website and below a selection of port installation. 
Here a list of "port install" commands that installed (under /opt/local) rather safely for me:

sudo port install wget
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

There are few exceptions (valid at this time, January 2013) such as the fortran compiler 
which is obtained from http://hpc.sourceforge.net
In my case the MLion (for Mac Os X 10.8.2) gcc4.8 is chosen as it has gfortran (with OpenMP):

wget http://prdownloads.sourceforge.net/hpc/gcc-mlion.tar.gz
sudo tar -xvfz gcc-mlion.tar.gz -C /. 
This will install it under /usr/local

OpenMPI:
--------
While OpenMP is standard and part of gcc/gfortran package, the MPI need to be installed and OpenMPI is recommended:

wget http://www.open-mpi.org/software/ompi/v1.6/downloads/openmpi-1.6.3.tar.gz
tar zxvf openmpi-1.6.3.tar.gz
./configure --prefix=/usr/local
make all
sudo make install

Test files with OpenMP and OpenMPI are compiled as follows:
mpif90 mpihello.F90 
mpif90 -fopenmp mpiomp_hello.F90 

Plotting with python:
---------------------
Python is a recommended plotting software as it is free and comprehensive and with a growing community also in NWP.
To plot on geography you can use the basemap lib (check its developer site here: http://matplotlib.org ).
This for me was installed (after having installed geos with port command and NetCDF/HDF5), more traditionnally as:

wget http://distfiles.macports.org/py-matplotlib-basemap/1.0.5_0/basemap-1.0.5.tar.gz
tar xvfz basemap-1.0.5.tar.gz
cd basemap-1.0.5
export GEOS_DIR=/opt/local/
python setup.py build
python setup.py install
sudo python setup.py install
sudo env HDF5_DIR=/opt/local NETCDF4_DIR=/opt/local /opt/local/bin/python setup.py install

for Grib the port is only partially working (at the moment, good for grib tools such as "grib_ls" or "grib_dump")

sudo port install grib_api

The manual installation of grib_api is however still the one recommended and it requires the packages:

wget http://www.ece.uvic.ca/~frodo/jasper/software/jasper-1.900.1.zip
unzip jasper-1.900.1.zip
cd jasper-1.900.1
configure
sudo make check install

wget https://software.ecmwf.int/wiki/download/attachments/3473437/grib_api-1.9.18.tar.gz
tar xvfz grib_api-1.9.18.tar.gz
cd grib_api-1.9.18
sed "s/-fno-common//g" >toto ; mv toto configure
configure --enable-python
sudo make check install

To connect grib and python software I used the libreary "pygrib" and ECMWF is developing a dedicated python library for grib:

wget http://pygrib.googlecode.com/files/pygrib-1.9.5.tar.gz
tar xvfz pygrib-1.9.5.tar.gz
cd pygrib-1.9.5
python setup.py build
sudo python setup.py install
python test.py

The compilation of fortran code need few adjustments in the config file:

CDFLIB =  -L/opt/local/lib -lnetcdff -fopenmp
CFLAGS = -m64 -arch x86_64 ...
FFLAGS = -c -m64 -arch x86_64 ...

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
To install one can use the port command:

sudo port install doxygen


Others:
-------
There are several Mac Users out there and a lot in NWP&Climate, that took the challenge of documenting installation procedures 
(eg. http://www.atmos.washington.edu/~salathe/osx_unix/ , so Google is a good companion to search for it!

------
Hope this is useful! Please write me if you see update needs or corrections (pad@ecmwf.int).
