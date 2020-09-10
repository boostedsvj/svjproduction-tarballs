# Creating tarballs for the SVJ/Production package

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
python manage setup 2017 gen
python manage setup 2017 miniaod
python manage setup 2018 gen  # gen and miniaod are the same CMSSW version for 2018
```

To update existing CMSSW directories:

```
python manage pull 2017 \*
python manage pull 2018 \*
```

To create tarballs:

```
python manage tarball 2017 \*
python manage tarball 2018 \*
```

To stageout all created tarballs:

```
python manage stageout
```

### For 2016

Be sure to login on an `el6` node. Repeat the commands above with the year switched to 2016.
