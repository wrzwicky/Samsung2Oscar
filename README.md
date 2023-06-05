# Samsung2Oscar

Convert Samsung Health data from files to something the [Oscar CPAP app](https://www.sleepfiles.com/OSCAR/) can import.

Intent is to import the entire Samsung Health history from exported files, and generate something Oscar can import and merge with existing CPAP data (as well as previous oxygen data.)

### WORKING:
- Reading Samsung oxygen saturation data.
- Export *a* spo2 file.

### NOT WORKING:
- Export *correct* spo2 file.
- Verify data matches up with CPAP data nicely.

.spo2 files only contain a single timestamp, then a list of samples expected to have been generated once every second. Samsung doesn't do that; instead every sample contains a time range and the min and max values observed during that time. There's no easy way to convert Samsung to Oscar.

### TODO:
- Find a better file format, write that.
- Verify data imports correctly.
- Verify repeated import of same data merges nicely.
- Verify imported data aligns with CPAP data usefully.
