MacTips
=======

Setup of MacPro (OS X 10.13, High Sierra) for Computing in Earth System Science 
----------------------------------------------------------------------------

Science libraries for Mac can be installed quite easily via the MacPorts project from http://www.macports.org
(To install it go to http://www.macports.org/install.php choose the Sierra version) and use then the "port install" command line. 
The software available is listed on the macports website and below a selection of ports installation. 
The Yosemite Java Runtime Environment provided by Apple is needed http://support.apple.com/kb/DL1572 . 
Here a list of "port install" commands that installed (under /opt/local) rather safely for me:

sudo port install wget

sudo port install grib_api

sudo port install hdf5

sudo port install netcdf

sudo port install netcdf-fortran

sudo port install ncview

sudo port install nco +netcdf

sudo port install cdo       

sudo port install xmgr

sudo port install xv

sudo port install gv

sudo port instal mpich

---


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

sudo port install grads

sudo port install metview


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
