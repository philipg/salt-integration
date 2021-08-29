cd package
zip -r ../deployment.zip .
cd ..
zip -g deployment.zip *.py
zip -g deployment.zip config/*
