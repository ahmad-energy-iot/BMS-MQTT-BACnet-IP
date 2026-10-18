// Example fragment for Node-RED settings.js.
// Merge into the existing module.exports configuration.
// Do not replace the complete settings.js file.

contextStorage: {
    default: "memoryOnly",
    memoryOnly: {
        module: "memory"
    },
    file: {
        module: "localfilesystem"
    }
},
