function uploadVideos() {
  var renameText = "Childern's Day";  // change this for each run

  var campaignParentId = "1tnp9MIjcSeYT9624k-7SHKoPkJpeI7ZW";   //Main school Link 

  var campaignParent = DriveApp.getFolderById(campaignParentId);

  function cleanString(s){ return s.toString().replace(/[^a-zA-Z0-9]/g,"").toLowerCase(); }

  function ensureAnyoneViewAndDownload(fileOrFolder) {
    var id = fileOrFolder.getId();
    try {
      fileOrFolder.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    } catch (e) {
      Logger.log("DriveApp.setSharing blocked (" + id + ").");
    }
    try {
      Drive.Files.patch(
        { copyRequiresWriterPermission: false, viewersCanCopyContent: true },
        id
      );
    } catch (e3) {
      Logger.log("Drive.Files.patch failed for " + id + ": " + e3);
    }
  }

  for (var i = startRow - 1; i < endRow && i < data.length; i++) {
    var groupName = (data[i][groupColIndex] || "").toString().trim();
    var rawId     = (data[i][idColIndex]    || "").toString().trim();
    var status    = (data[i][statusColIndex]|| "").toString().trim();
    var linkCell  = (data[i][linkColIndex]  || "").toString().trim();

    if (status.toLowerCase() !== "done") {
      Logger.log("Skipping row " + (i+1) + " (status not done)");
      continue;
    }

    var cleanedId = cleanString(rawId);

    // Find the source video in master folder
    var foundFile = null;
    var files = masterFolder.getFiles();
    while (files.hasNext()) {
      var f = files.next();
      var nameNoExt = f.getName().replace(/\.[^/.]+$/,"");
      if (cleanString(nameNoExt) === cleanedId) { foundFile = f; break; }
    }
    if (!foundFile) { 
      Logger.log("No video found for " + cleanedId); 
      continue; 
    }

    // Ensure group folder exists
    var groupFolders = campaignParent.getFoldersByName(groupName);
    var groupFolder = groupFolders.hasNext() ? groupFolders.next() : campaignParent.createFolder(groupName);

    // Expected video name (renameText.mp4)
    var expectedName = renameText + ".mp4";

    // 🔥 Delete any existing video with same name
    var existingFiles = groupFolder.getFilesByName(expectedName);
    while (existingFiles.hasNext()) {
      var oldFile = existingFiles.next();
      try {
        oldFile.setTrashed(true);
        Logger.log("Deleted existing video: " + expectedName + " in " + groupName);
      } catch (e) {
        Logger.log("Failed to delete existing video: " + e);
      }
    }

    // Copy new video
    var newFile = foundFile.makeCopy(expectedName, groupFolder);
    Logger.log("Copied new video: " + newFile.getName() + " to " + groupName);

    // Set permissions
    ensureAnyoneViewAndDownload(groupFolder);
    ensureAnyoneViewAndDownload(newFile);

    // Update link cell with folder link
    sheet.getRange(i+1, linkColIndex+1).setValue(groupFolder.getUrl());
    SpreadsheetApp.flush();
    Logger.log("Updated link for row " + (i+1));
  }

  Logger.log("Script finished successfully");
}
