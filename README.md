# Check-codes
Check codes between svn and reviewboard after committing.

Project background:
To ensure quality of the code, when programmers creating or revising the code, they shuould post the changes to other experts to
 ship it before committing to the SVN. However, programmers often make diffcult to ensure the coherence between the committing 
 code to SVN and the posting code on Reviewboard.

Project goal:
Check the codes between SVN and Reviewboard. After committing the code to SVN, a python-script will work and the results will be 
emailed to relevant people.

Project processes:
1.Use python2.7 to modify SVN/repository/hooks/post-commit.
2.Check out the code from SVN and download the code from Reviewboard.
3.Use diff tool to make difference between the two.
4.Print the log for recording.
5.Email the log to relevant people automatically.

Project files:
1.post-commit.py
2.post-commit_cfg.ini
