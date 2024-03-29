const gulp = require('gulp')
const uglify = require('gulp-uglify')
const del = require('del')
const sass = require('gulp-sass')(require('sass'))
const filelog = require('gulp-filelog')
const include = require('gulp-include')
const path = require('path')

// Paths
let environment
const repoRoot = path.join(__dirname)
const npmRoot = path.join(repoRoot, 'node_modules')
const govukFrontendRoot = path.join(npmRoot, 'govuk-frontend')
const assetsFolder = path.join(repoRoot, 'app', 'assets')
const staticFolder = path.join(repoRoot, 'app', 'static')
const govukFrontendFontsFolder = path.join(govukFrontendRoot, 'govuk', 'assets', 'fonts')
const govukFrontendImageFolder = path.join(govukFrontendRoot, 'govuk', 'assets', 'images')

// JavaScript paths
const jsSourceFile = path.join(assetsFolder, 'javascripts', 'application.js')
const jsDistributionFolder = path.join(staticFolder, 'javascripts')
const jsDistributionFile = 'application.js'

// CSS paths
const cssSourceGlob = path.join(assetsFolder, 'scss', 'application*.scss')
const cssDistributionFolder = path.join(staticFolder, 'stylesheets')

// Configuration
const sassOptions = {
  development: {
    outputStyle: 'expanded',
    lineNumbers: true,
    includePaths: [
      assetsFolder + '/scss',
      govukFrontendRoot
    ],
    sourceComments: true,
    errLogToConsole: true
  },
  production: {
    outputStyle: 'compressed',
    lineNumbers: true,
    includePaths: [
      assetsFolder + '/scss',
      govukFrontendRoot
    ]
  }
}

const uglifyOptions = {
  development: {
    mangle: false,
    output: {
      beautify: true,
      semicolons: true,
      comments: true,
      indent_level: 2
    },
    compress: false
  },
  production: {
    mangle: true
  }
}

const logErrorAndExit = function logErrorAndExit (err) {
  // coloured text: https://coderwall.com/p/yphywg/printing-colorful-text-in-terminal-when-run-node-js-script
  console.log('\x1b[41m\x1b[37m  Error: ' + err.message + '\x1b[0m')
  process.exit(1)
}

gulp.task('clean:js', function () {
  return del(jsDistributionFolder + '/**/*').then(function (paths) {
    console.log('💥  Deleted the following JavaScript files:\n', paths.join('\n'))
  })
})

gulp.task('clean:css', function () {
  return del(cssDistributionFolder + '/**/*').then(function (paths) {
    console.log('💥  Deleted the following CSS files:\n', paths.join('\n'))
  })
})

gulp.task('clean', gulp.parallel('clean:js', 'clean:css'))

gulp.task('sass', function () {
  const stream = gulp.src(cssSourceGlob)
    .pipe(filelog('Compressing SCSS files'))
    .pipe(
      sass(sassOptions[environment]))
    .on('error', logErrorAndExit)
    .pipe(gulp.dest(cssDistributionFolder))

  stream.on('end', function () {
    console.log('💾  Compressed CSS saved as .css files in ' + cssDistributionFolder)
  })

  return stream
})

gulp.task('js', function () {
  const stream = gulp.src(jsSourceFile, { sourcemaps: true })
    .pipe(filelog('Compressing JavaScript files'))
    .pipe(include({ hardFail: true }))
    .pipe(uglify(
      uglifyOptions[environment]
    ))
    .pipe(gulp.dest(jsDistributionFolder, { sourcemaps: 'maps' }))

  stream.on('end', function () {
    console.log('💾 Compressed JavaScript saved as ' + jsDistributionFolder + '/' + jsDistributionFile)
  })

  return stream
})

function copyFactory (resourceName, sourceFolder, targetFolder) {
  return function () {
    return gulp
      .src(sourceFolder + '/**/*', { base: sourceFolder })
      .pipe(gulp.dest(targetFolder))
      .on('end', function () {
        console.log('📂  Copied ' + resourceName)
      })
  }
}

gulp.task(
  'copy:images',
  copyFactory(
    'image assets from app to static folder',
    assetsFolder + '/images',
    staticFolder + '/images'
  )
)

gulp.task(
  'copy:svg',
  copyFactory(
    'image assets from app to static folder',
    assetsFolder + '/svg',
    staticFolder + '/svg'
  )
)

gulp.task(
  'copy:govuk_frontend_assets:fonts',
  copyFactory(
    'fonts from the GOVUK frontend assets',
    govukFrontendFontsFolder,
    staticFolder + '/fonts'
  )
)

gulp.task(
  'copy:govuk_frontend_assets:images',
  copyFactory(
    'images from the GOVUK frontend',
    govukFrontendImageFolder,
    path.join(staticFolder, 'images')
  )
)

gulp.task('set_environment_to_development', function (cb) {
  environment = 'development'
  cb()
})

gulp.task('set_environment_to_production', function (cb) {
  environment = 'production'
  cb()
})

gulp.task('copy', gulp.parallel(
  'copy:images',
  'copy:svg',
  'copy:govuk_frontend_assets:fonts',
  'copy:govuk_frontend_assets:images'
))

gulp.task('compile', gulp.series('copy', gulp.parallel('sass', 'js')))

gulp.task('build:development', gulp.series(gulp.parallel('set_environment_to_development', 'clean'), 'compile'))

gulp.task('build:production', gulp.series(gulp.parallel('set_environment_to_production', 'clean'), 'compile'))

gulp.task('watch', gulp.series('build:development', function () {
  const jsWatcher = gulp.watch([assetsFolder + '/**/*.js'], gulp.series('js'))
  const cssWatcher = gulp.watch([assetsFolder + '/**/*.scss'], gulp.series('sass'))
  const dmWatcher = gulp.watch([npmRoot + '/digitalmarketplace-frameworks/**'], gulp.series('copy:frameworks'))
  const notice = function (event) {
    console.log('File ' + event.path + ' was ' + event.type + ' running tasks...')
  }

  cssWatcher.on('change', notice)
  jsWatcher.on('change', notice)
  dmWatcher.on('change', notice)
}))
