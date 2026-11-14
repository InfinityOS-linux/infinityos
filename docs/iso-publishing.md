# Publishing ISO images

Run **Build verified InfinityOS ISOs** on `main` after the RPM publication has
succeeded for the same commit. Both architectures are built and verified before
publication. GitHub artifacts remain available for seven days.

The final job uploads both images and their SHA-256/MD5 files to Cloudflare R2
under `releases/<full commit>/`. `latest.json` changes only after both uploads
have succeeded and their sizes and hash metadata have been checked. Each release
also has an immutable `manifest.json`, so download links can remain tied to the
checksums displayed when the user opened the website.

Configure these repository variables:

- `R2_ACCOUNT_ID`: Cloudflare account ID.
- `R2_BUCKET`: bucket dedicated to public InfinityOS releases.
- `R2_PUBLIC_URL`: HTTPS custom domain attached to that bucket, without a path.

Configure `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` as repository secrets.
Use an R2 Object Read & Write credential scoped only to the release bucket.
The website reads the public manifest and needs no R2 credentials. After a
complete pair is promoted in `latest.json`, the publisher removes objects from
older commit releases. Failed builds or uploads leave the previous release in
place. A browser tab opened before promotion may display the previous checksums;
refresh the page before downloading a new release.

The runner uses its preinstalled AWS CLI with multipart uploads, so ISO files
larger than 5 GB do not need to be split for users. Upload credentials are passed
only to the publication step.
