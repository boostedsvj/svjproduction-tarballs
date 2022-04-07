# Creating tarballs for the SVJ/Production and TreeMaker packages

This is a small script to manage tarball generation. It relies on the `qondor` package being installed.

## Setup

```
virtualenv myenv
source myenv/bin/activate
pip install qondor
git clone git@github.com:boostedsvj/svjproduction-tarballs.git
```

## Usage

To setup the CMSSW from scratch:

```
python manage.py setup 2016 miniaod
python manage.py setup 2017 gen
python manage.py setup 2017 miniaod
python manage.py setup 2018 gen  # gen and miniaod are the same CMSSW version for 2018
python manage.py setup 2018UL miniaod  # UL
python manage.py setup treemaker
```

To update existing CMSSW directories:

```
python manage.py pull 2016 miniaod
python manage.py pull 2017 \*
python manage.py pull 2018 \*
python manage.py pull treemaker
```

To create tarballs:

```
python manage.py tarball 2016 miniaod
python manage.py tarball 2017 \*
python manage.py tarball 2018 \*
python manage.py tarball treemaker
```

To stageout all created tarballs:

```
python manage.py stageout
```

### For 2016 GEN-SIM and slc6 tarballs

On the LPC, first setup the singularity container:

```
cmssw-slc6 -B /uscms_data/d3/klijnsma:/nobackup # Exchange with your own username, nobackup mount net strictly necessary
```

Install `qondor` (`virtualenv` is typically not available on `slc6`):

```
mkdir -p el6installs/bin
mkdir -p el6installs/lib/python2.6/site-packages
export PATH="${PWD}/el6installs/bin:${PATH}"
export PYTHONPATH="${PWD}/el6installs/lib/python2.6/site-packages:${PYTHONPATH}"
pip install --install-option="--prefix=${PWD}/el6installs" --no-cache-dir qondor
```

Then call the python script:

```
python manage.py setup 2016 gen
# python manage.py pull 2016 gen  # to update
python manage.py tarball 2016 miniaod
python stageout
```
