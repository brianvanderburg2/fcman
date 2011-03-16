// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include "config.h"

#include <wx/defs.h>
#include <wx/artprov.h>
#include <wx/cmdline.h>
#include <wx/fileconf.h>
#include <wx/filefn.h>
#include <wx/filename.h>
#include <wx/intl.h>
#include <wx/log.h>
#include <wx/stdpaths.h>
#include <wx/utils.h>


#include "app.h"
#include "mainwnd.h"
#include "options.h"


IMPLEMENT_APP(Application);

// Constructor
Application::Application() :
    m_config(NULL),
    m_options(NULL)
{
}

// Destructor
Application::~Application()
{
}

// Setup the application
bool Application::OnInit()
{
    // Set application information
    SetAppName(wxT(APP_NAME));
    SetAppDisplayName(wxT(APP_DISPLAY_NAME));

    // Base init to deal with command line
    if(!wxApp::OnInit())
    {
        return false;
    }

    // Create user directories
    CreateUserDirs();

    // Create config
    m_config = new wxFileConfig(GetAppName(), GetVendorName(), GetConfigFile(), wxEmptyString, wxCONFIG_USE_LOCAL_FILE);
    wxConfigBase::Set(m_config);

    // Load options
    m_options = new Options();
    m_options->Load(m_config);

    // Create main window
    MainWindow* wnd = new MainWindow;
    wnd->Show(true);
    SetTopWindow(wnd);

    // Open file if needed
    if(!m_file.IsEmpty())
        wnd->OpenFile(m_file);

    return true;
}

// Close down the application
int Application::OnExit()
{
    // Save options
    m_options->Save(m_config);
    delete m_options;
    m_options = NULL;

    // Save config
    wxConfig::DontCreateOnDemand();
    wxConfigBase::Set(NULL);
    m_config->Flush();
    delete m_config;
    m_config = NULL;

    // Normal shutdown
    return wxApp::OnExit();
}

// Initialize command line
void Application::OnInitCmdLine(wxCmdLineParser& parser)
{
    wxApp::OnInitCmdLine(parser);

    // Paths options
    parser.AddOption(wxT(""), wxT("appdatadir"), _("location of application data directory"), wxCMD_LINE_VAL_STRING);
    parser.AddOption(wxT(""), wxT("userdatadir"), _("location of the user data directory"), wxCMD_LINE_VAL_STRING);

    // Files
    parser.AddParam(wxT("file(s) to open"), wxCMD_LINE_VAL_STRING, wxCMD_LINE_PARAM_OPTIONAL);
}

// Process command line
bool Application::OnCmdLineParsed(wxCmdLineParser& parser)
{
    if(!wxApp::OnCmdLineParsed(parser))
    {
        parser.Usage();
        return false;
    }

    // Remember paths
    wxString path;
    wxFileName fn;

    if(parser.Found(wxT("appdatadir"), &path))
    {
        fn.AssignDir(path);
        fn.Normalize();
        m_appDataDir = fn.GetPath();
    }
    else
    {
        m_appDataDir = wxStandardPaths::Get().GetDataDir();
    }

    if(parser.Found(wxT("userdatadir"), &path))
    {
        fn.AssignDir(path);
        fn.Normalize();
        m_userDataDir = fn.GetPath();
    }
    else
    {
        m_userDataDir = wxStandardPaths::Get().GetUserDataDir();
    }

    m_docDataDir = GetAppDataPath(wxT("doc/"), wxPATH_UNIX);
    m_pixmapDataDir = GetAppDataPath(wxT("pixmaps/"), wxPATH_UNIX);

    // File to open
    if(parser.GetParamCount() > 0)
    {
        fn.Assign(parser.GetParam(0));
        fn.Normalize();

        m_file = fn.GetFullPath();
    }

    return true;
}

// Application data directory
wxString Application::GetAppDataPath(const wxString& path, wxPathFormat format)
{
    wxFileName fn(path, format);
    fn.MakeAbsolute(m_appDataDir);

    return fn.GetFullPath();
}

wxString Application::GetUserDataPath(const wxString& path, wxPathFormat format)
{
    wxFileName fn(path, format);
    fn.MakeAbsolute(m_userDataDir);

    return fn.GetFullPath();
}

// Location of image files
wxString Application::GetPixmapDataPath(const wxString& path, wxPathFormat format)
{
    wxFileName fn(path, format);
    fn.MakeAbsolute(m_pixmapDataDir);

    return fn.GetFullPath();
}

// Location of doc files
wxString Application::GetDocPath(const wxString& path, wxPathFormat format)
{
    wxFileName fn(path, format);
    fn.MakeAbsolute(m_docDataDir);

    return fn.GetFullPath();
}

// Location of a help file
wxString Application::GetHelpFile()
{
    return GetDocPath(wxT("index.html"));
}

// Location of the configuration file
wxString Application::GetConfigFile()
{
    return GetUserDataPath(wxT("config.ini"));
}

// Create user diectories
void Application::CreateUserDirs()
{
    if(!wxFileName::Mkdir(GetUserDataPath(), 0777, wxPATH_MKDIR_FULL))
    {
        ::wxLogError(_("Unable to create user data directory"));
    }
}

