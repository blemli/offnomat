set -e

echo "~~~ install antiwhine timer ~~~~"
sudo cp -f setup/offnomat-antiwhine.service setup/offnomat-antiwhine.timer /lib/systemd/system/
sudo chmod 644 /lib/systemd/system/offnomat-antiwhine.service /lib/systemd/system/offnomat-antiwhine.timer
sudo systemctl daemon-reload
sudo systemctl enable --now offnomat-antiwhine.timer
